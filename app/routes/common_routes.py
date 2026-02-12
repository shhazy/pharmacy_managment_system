from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from typing import List

from ..models import Category, Manufacturer, Store, Supplier, Patient, Invoice, StockInventory, Product, InvoiceItem, RegulatoryLog, User, Role, PharmacySettings, AppSettings
from ..schemas import InvoiceCreate, RoleResponse
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

# Categories and Manufacturers (at root for compatibility)
@router.get("/categories")
def get_categories(db: Session = Depends(get_db_with_tenant)):
    return db.query(Category).all()

@router.get("/manufacturers")
def get_manufacturers(db: Session = Depends(get_db_with_tenant)):
    return db.query(Manufacturer).all()

@router.get("/purchase-conversion-units")
def list_purchase_conversion_units(db: Session = Depends(get_db_with_tenant)):
    from ..models.inventory_models import PurchaseConversionUnit
    return db.query(PurchaseConversionUnit).filter(PurchaseConversionUnit.is_active == True).all()

# Stores (at root for compatibility)
@router.get("/stores")
def list_stores(db: Session = Depends(get_db_with_tenant)):
    return db.query(Store).all()

@router.post("/stores")
def create_store(name: str, address: str, is_warehouse: bool = False, db: Session = Depends(get_db_with_tenant)):
    store = Store(name=name, address=address, is_warehouse=is_warehouse)
    db.add(store)
    db.flush()
    store_id = store.id
    db.commit()
    # db.refresh(store)
    store = db.query(Store).filter(Store.id == store_id).first()
    return store

# Suppliers (at root for compatibility)
@router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db_with_tenant)):
    return db.query(Supplier).all()

@router.post("/suppliers")
def add_supplier(name: str, address: str, gst: str, db: Session = Depends(get_db_with_tenant)):
    sup = Supplier(name=name, address=address, gst_number=gst)
    db.add(sup)
    db.flush()
    sup_id = sup.id
    db.commit()
    # db.refresh(sup)
    
    # Restore tenant search path
    tenant_schema = db.info.get('tenant_schema')
    if tenant_schema:
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))

    sup = db.query(Supplier).filter(Supplier.id == sup_id).first()
    return sup

# Patients (at root for compatibility)
@router.get("/patients")
def list_patients(db: Session = Depends(get_db_with_tenant)):
    return db.query(Patient).all()

@router.post("/patients")
def add_patient(p_name: str, p_phone: str, db: Session = Depends(get_db_with_tenant)):
    p = Patient(name=p_name, phone=p_phone)
    db.add(p)
    db.flush()
    p_id = p.id
    db.commit()
    # db.refresh(p)
    
    # Restore tenant search path
    tenant_schema = db.info.get('tenant_schema')
    if tenant_schema:
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))

    p = db.query(Patient).filter(Patient.id == p_id).first()
    return p

# Invoices (at root for compatibility)
@router.post("/invoices")
def create_invoice(inv_in: InvoiceCreate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    from datetime import datetime
    import traceback
    from fastapi import HTTPException
    
    try:
        # CRITICAL: Prevent object expiration on commit. 
        # AccountingService.record_sale_transaction() calls db.commit(), which normally expires objects.
        # This causes subsequent access to hit the DB. If the search_path was reset by the DB on commit,
        # it might hit public.invoices (which is missing customer_id) instead of tenant.invoices.
        db.expire_on_commit = False
        
        sub_total = 0
        tax_total = 0
        invoice_items = []
        returned_items_data = [] # To track items for SalesReturn model
        
        for item in inv_in.items:
            # batch_id in request maps to inventory_id in StockInventory
            inv_item = db.query(StockInventory).filter(
                StockInventory.inventory_id == item.batch_id, 
                StockInventory.product_id == item.medicine_id
            ).first()
            
            if not inv_item:
                raise HTTPException(status_code=400, detail=f"Batch {item.batch_id} not found for product {item.medicine_id}")
            
            # If quantity is positive (Sale), check stock
            if item.quantity > 0 and inv_item.quantity < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {item.medicine_id} batch {item.batch_id}")
            
            # Deduct stock (Subtracting a negative quantity increases stock - perfect for returns)
            inv_item.quantity -= item.quantity
            
            line_total = item.unit_price * item.quantity
            tax = line_total * (item.tax_percent / 100)
            sub_total += line_total
            tax_total += tax
            
            # Item level discount
            if item.discount_percent > 0:
                disc = line_total * (item.discount_percent / 100)
            else:
                disc = item.discount_amount
            
            item_net = line_total + tax - disc
            
            invoice_items.append(InvoiceItem(
                medicine_id=item.medicine_id, 
                batch_id=item.batch_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                retail_price=item.retail_price,
                tax_amount=tax,
                discount_percent=item.discount_percent,
                discount_amount=disc if item.discount_percent == 0 else 0,
                total_price=item_net
            ))

            # Track for SalesReturn if it's a return line
            if item.quantity < 0:
                returned_items_data.append({
                    "product_id": item.medicine_id,
                    "batch_id": item.batch_id,
                    "quantity": abs(item.quantity),
                    "unit_price": item.unit_price,
                    "retail_price": item.retail_price,
                    "tax_amount": abs(tax),
                    "total_price": abs(item_net)
                })
            
            med = db.query(Product).get(item.medicine_id)
            if med.control_drug and item.quantity > 0:
                db.add(RegulatoryLog(medicine_id=med.id, action="Dispensed", quantity=item.quantity, patient_id=inv_in.patient_id, customer_id=inv_in.customer_id))
            elif med.control_drug and item.quantity < 0:
                db.add(RegulatoryLog(medicine_id=med.id, action="Returned", quantity=abs(item.quantity), patient_id=inv_in.patient_id, customer_id=inv_in.customer_id))

        # Net total calculation: (Gross Items) + (Adjustment) - (Invoice Discount)
        # Note: adjustment can be positive (charge) or negative (discount)
        items_net_sum = sum(it.total_price for it in invoice_items)
        net_total = items_net_sum + inv_in.adjustment - inv_in.invoice_discount
        
        # Ensure we don't double count if discount_amount was just a proxy for invoice_discount
        # Actually, let's just use the fields explicitly.
        # net_total = items_net_sum + inv_in.adjustment - inv_in.invoice_discount
        # This matches the frontend: baseNetTotal = grossTotal + adjustment; netTotal = baseNetTotal - invoiceDiscount;
        
        # Auto-increment Invoice Number - Filter to only look at standard INV sequence (starts with 0 for now)
        last_invoice = db.query(Invoice).filter(Invoice.invoice_number.like('INV-0%')).order_by(Invoice.invoice_number.desc()).first()
        new_invoice_number = "INV-000001"
        if last_invoice and last_invoice.invoice_number:
            import re
            # Extract numeric part
            match = re.search(r'INV-(\d+)', last_invoice.invoice_number)
            if match:
                num_part = match.group(1)
                # Check if it's a sequence vs timestamp (10+ digits)
                if len(num_part) < 10: 
                    try:
                        next_seq = int(num_part) + 1
                        new_invoice_number = f"INV-{next_seq:06d}"
                    except ValueError:
                        pass

        new_inv = Invoice(
            invoice_number=new_invoice_number,
            patient_id=inv_in.patient_id,
            customer_id=inv_in.customer_id,
            customer_name=inv_in.customer_name,
            user_id=user.id,
            store_id=user.store_id,
            sub_total=sub_total,
            tax_amount=tax_total,
            discount_amount=inv_in.discount_amount,
            invoice_discount=inv_in.invoice_discount,
            net_total=net_total,
            paid_amount=net_total,
            status=inv_in.status,
            payment_method=inv_in.payment_method,
            cash_register_session_id=inv_in.cash_register_session_id,
            remarks=inv_in.remarks,
            items=invoice_items
        )
        db.add(new_inv)
        db.flush()
        
        # --- Handle SalesReturn Model for Audit ---
        if returned_items_data:
            from ..models.sales_models import SalesReturn, SaleReturnItem
            
            # Calculate return totals from the negative lines
            ret_sub = sum(d['total_price'] for d in returned_items_data) # This is absolute value
            
            sales_ret = SalesReturn(
                return_number=f"REV-{datetime.now().strftime('%y%m%d%H%M%S')}",
                invoice_id=new_inv.id,
                sub_total=ret_sub,
                tax_amount=0.0, # Simplified: tax already reflected in item.total_price reversal
                net_total=ret_sub,
                reason="POS Return/Exchange",
                remarks=inv_in.remarks
            )
            db.add(sales_ret)
            db.flush()
            
            for r_item in returned_items_data:
                db.add(SaleReturnItem(
                    sales_return_id=sales_ret.id,
                    product_id=r_item['product_id'],
                    batch_id=r_item['batch_id'],
                    quantity=r_item['quantity'],
                    unit_price=r_item['unit_price'],
                    retail_price=r_item.get('retail_price'),
                    tax_amount=r_item.get('tax_amount', 0.0),
                    total_price=r_item['total_price']
                ))
            
            db.flush() # Ensure sales_ret.id is ready for accounting

        new_inv_id = new_inv.id
        print(f"--- TRACE: Invoice {new_inv.invoice_number} prepared. Starting accounting...")
        
        # Create accounting entry
        try:
            from ..services.accounting_service import AccountingService
            
            # The new record_sale_transaction is "Return-Aware" and handles 
            # the net financials, revenue reversals, and inventory restock
            # for the entire invoice (including exchanges) in ONE balanced entry.
            sale_entry = AccountingService.record_sale_transaction(db, new_inv, user.id)
            
            print(f"--- TRACE: Accounting processed for POS Transaction {new_inv.invoice_number}")
            db.commit() # FINAL COMMIT for everything
            print(f"✓ DONE: Transaction {new_inv.invoice_number} fully recorded.")
            
            # Safer Refresh: Manually restore path and fetch to avoid UndefinedColumn errors
            tenant_schema = db.info.get('tenant_schema')
            if tenant_schema:
                try:
                    db.execute(text(f"SET search_path TO {tenant_schema}, public"))
                    # Use a fresh query to avoid any stale data or expired attribute issues
                    refreshed_inv = db.query(Invoice).options(
                        joinedload(Invoice.items).joinedload(InvoiceItem.product)
                    ).filter(Invoice.id == new_inv_id).first()
                    if refreshed_inv:
                        new_inv = refreshed_inv
                        # Enrich items with product_name for serialization consistency
                        for item in new_inv.items:
                            if item.product:
                                setattr(item, "product_name", item.product.product_name)
                except Exception as refresh_err:
                    print(f"⚠ Warning: Manual refresh failed: {refresh_err}")
                    # If refresh fails, we still have the object from before commit (thanks to expire_on_commit=False)
        except Exception as acc_err:
            print(f"⚠ Warning: Failed to create accounting entry: {acc_err}")
            traceback.print_exc()
            
            # Restore path even on accounting failure
            tenant_schema = db.info.get('tenant_schema')
            if tenant_schema:
                try:
                    db.execute(text(f"SET search_path TO {tenant_schema}, public"))
                except: pass
        
        # Build clean response dict to avoid circular reference issues
        response = {
            "id": new_inv.id,
            "invoice_number": new_inv.invoice_number,
            "customer_name": new_inv.customer_name,
            "sub_total": new_inv.sub_total,
            "tax_amount": new_inv.tax_amount,
            "discount_amount": new_inv.discount_amount,
            "invoice_discount": new_inv.invoice_discount,
            "net_total": new_inv.net_total,
            "paid_amount": new_inv.paid_amount,
            "payment_method": new_inv.payment_method,
            "status": new_inv.status,
            "created_at": new_inv.created_at.isoformat() if new_inv.created_at else None,
            "items": []
        }
        
        # Safely serialize items
        for item in new_inv.items:
            item_dict = {
                "id": item.id,
                "medicine_id": item.medicine_id,
                "batch_id": item.batch_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "retail_price": item.retail_price,
                "tax_amount": item.tax_amount,
                "discount_percent": item.discount_percent,
                "discount_amount": item.discount_amount,
                "total_price": item.total_price,
                "product_name": getattr(item, "product_name", item.product.product_name if item.product else None)
            }
            response["items"].append(item_dict)
        
        return response
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/invoices")
def list_invoices(
    limit: int = 50, 
    start_date: str | None = None, 
    end_date: str | None = None, 
    status: str | None = None, 
    db: Session = Depends(get_db_with_tenant)
):
    """List recent invoices for the POS history view with filters"""
    query = db.query(Invoice)
    
    if status and status != 'All':
        query = query.filter(Invoice.status == status)
        
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Invoice.created_at >= start)
        except: pass
        
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) # inclusive
            query = query.filter(Invoice.created_at < end)
        except: pass
        
    invoices = query.order_by(Invoice.created_at.desc()).limit(limit).options(
        joinedload(Invoice.items).joinedload(InvoiceItem.product),
        joinedload(Invoice.user)
    ).all()
    
    # Enrich and serialize
    inv_list = []
    for inv in invoices:
        inv_dict = {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "created_at": inv.created_at,
            "status": inv.status,
            "sub_total": inv.sub_total,
            "tax_amount": inv.tax_amount,
            "discount_amount": inv.discount_amount,
            "net_total": inv.net_total,
            "payment_method": inv.payment_method,
            "customer_name": inv.customer_name,
            "remarks": inv.remarks,
            "user": {"name": inv.user.username if inv.user else "ADMIN"},
            "items": []
        }
        
        for item in inv.items:
            # Calculate tax percent if missing (backwards calculation)
            tax_pct = 0
            base_val = item.unit_price * item.quantity
            if base_val > 0 and item.tax_amount > 0:
                try: tax_pct = round((item.tax_amount / base_val) * 100, 2)
                except: pass

            item_dict = {
                "id": item.id,
                "medicine_id": item.medicine_id,
                "batch_id": item.batch_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "retail_price": item.retail_price,
                "tax_amount": item.tax_amount,
                "tax_percent": tax_pct,
                "discount_percent": getattr(item, 'discount_percent', 0),
                "discount_amount": getattr(item, 'discount_amount', 0),
                "total_price": item.total_price,
                "product_name": item.product.product_name if item.product else f"Item {item.medicine_id}"
            }
            inv_dict["items"].append(item_dict)
        inv_list.append(inv_dict)
                    
    return inv_list

@router.delete("/invoices/{invoice_id}")
def void_invoice(invoice_id: int, db: Session = Depends(get_db_with_tenant)):
    """Void an invoice and restore stock (used for Recalling Held bills)"""
    # Find invoice
    inv = db.query(Invoice).options(joinedload(Invoice.items)).filter(Invoice.id == invoice_id).first()
    if not inv:
        return {"message": "Invoice not found"}
        
    # Restore stock
    for item in inv.items:
        stock = db.query(StockInventory).filter(
            StockInventory.inventory_id == item.batch_id,
            StockInventory.product_id == item.medicine_id
        ).first()
        if stock:
            stock.quantity += item.quantity
            
    # Delete invoice (or mark void, but for HOLD recall we delete it because we re-add to cart)
    db.delete(inv)
    db.commit()
    return {"message": "Invoice voided and stock restored"}

@router.put("/invoices/{invoice_id}")
def update_invoice(invoice_id: int, inv_in: InvoiceCreate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    """Update an existing invoice (used for modifying Held bills)"""
    import traceback
    from fastapi import HTTPException
    
    try:
        # 1. Fetch existing invoice
        inv = db.query(Invoice).options(joinedload(Invoice.items)).filter(Invoice.id == invoice_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # 2. Revert stock for all existing items and delete them
        for item in inv.items:
            stock = db.query(StockInventory).filter(
                StockInventory.inventory_id == item.batch_id,
                StockInventory.product_id == item.medicine_id
            ).first()
            if stock:
                stock.quantity += item.quantity
            db.delete(item)
        
        # 3. Add new items and deduct stock
        sub_total = 0
        tax_total = 0
        invoice_items = []
        
        for item in inv_in.items:
            # batch_id in request maps to inventory_id in StockInventory
            inv_item = db.query(StockInventory).filter(
                StockInventory.inventory_id == item.batch_id, 
                StockInventory.product_id == item.medicine_id
            ).first()
            if not inv_item or inv_item.quantity < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {item.medicine_id} batch {item.batch_id}")
            
            inv_item.quantity -= item.quantity
            line_total = item.unit_price * item.quantity
            tax = line_total * (item.tax_percent / 100)
            sub_total += line_total
            tax_total += tax
            
            # Item level discount
            if item.discount_percent > 0:
                disc = line_total * (item.discount_percent / 100)
            else:
                disc = item.discount_amount
            
            item_net = line_total + tax - disc
            
            new_item = InvoiceItem(
                invoice_id=inv.id,
                medicine_id=item.medicine_id, 
                batch_id=item.batch_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item_net
            )
            db.add(new_item)
            invoice_items.append(new_item)
            
            med = db.query(Product).get(item.medicine_id)
            if med.control_drug:
                db.add(RegulatoryLog(medicine_id=med.id, action="Dispensed", quantity=item.quantity, patient_id=inv_in.patient_id))

        # 4. Update Invoice Totals
        items_net_sum = sum(it.total_price for it in invoice_items)
        net_total = items_net_sum - inv_in.discount_amount
        
        inv.sub_total = sub_total
        inv.tax_amount = tax_total
        inv.discount_amount = inv_in.discount_amount
        inv.net_total = net_total
        inv.paid_amount = net_total
        inv.status = inv_in.status
        inv.payment_method = inv_in.payment_method
        inv.updated_at = datetime.utcnow()
        
        db.commit()
        # db.refresh(inv)
        
        # Restore tenant search path
        tenant_schema = db.info.get('tenant_schema')
        if tenant_schema:
            db.execute(text(f"SET search_path TO {tenant_schema}, public"))

        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        return inv

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stock/transfer")
def transfer_stock(from_id: int, to_id: int, med_id: int, qty: int, db: Session = Depends(get_db_with_tenant)):
    from fastapi import HTTPException
    from ..models import StockTransfer
    
    # Simple logic: find first available inventory in source store
    inv_item = db.query(StockInventory).filter(
        StockInventory.product_id == med_id, 
        StockInventory.store_id == from_id,
        StockInventory.quantity >= qty
    ).first()
    
    if not inv_item:
        raise HTTPException(status_code=400, detail="Insufficient stock at source branch")
    
    inv_item.quantity -= qty
    
    # Create new inventory entry at destination or update if same batch exists
    dest_inv = db.query(StockInventory).filter(
        StockInventory.product_id == med_id,
        StockInventory.store_id == to_id,
        StockInventory.batch_number == inv_item.batch_number
    ).first()
    
    if dest_inv:
        dest_inv.quantity += qty
    else:
        new_inv = StockInventory(
            product_id=med_id,
            store_id=to_id,
            batch_number=inv_item.batch_number,
            expiry_date=inv_item.expiry_date,
            quantity=qty,
            unit_cost=inv_item.unit_cost,
            selling_price=inv_item.selling_price,
            grn_id=inv_item.grn_id
        )
        db.add(new_inv)
        
    transfer = StockTransfer(from_store_id=from_id, to_store_id=to_id, medicine_id=med_id, quantity=qty)
    db.add(transfer); db.commit()
    return {"message": "Transfer successful"}

# Reports (at root for compatibility)
@router.get("/reports/daily-sales")
def get_daily_sales(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sales = db.query(func.sum(Invoice.net_total)).filter(Invoice.created_at >= today).scalar() or 0
    count = db.query(func.count(Invoice.id)).filter(Invoice.created_at >= today).scalar() or 0
    return {"total_sales": sales, "invoice_count": count}

@router.get("/reports/expiry-alerts")
def get_expiry_alerts(db: Session = Depends(get_db_with_tenant)):
    next_90_days = datetime.utcnow() + timedelta(days=90)
    return db.query(StockInventory).join(Product).filter(
        StockInventory.expiry_date <= next_90_days, 
        StockInventory.quantity > 0
    ).all()

@router.get("/reports/low-stock")
def get_low_stock(db: Session = Depends(get_db_with_tenant)):
    return db.query(Product).join(StockInventory).group_by(Product.id).having(
        func.sum(StockInventory.quantity) <= Product.reorder_level
    ).all()

# --- SETTINGS ROUTES ---
from ..models.pharmacy_models import PharmacySettings
from pydantic import BaseModel

class SettingsUpdate(BaseModel):
    name: str | None = None
    tagline: str | None = None
    phone_no: str | None = None
    license_no: str | None = None
    address: str | None = None
    email: str | None = None
    logo_url: str | None = None
    theme_config: dict | None = None

@router.get("/settings")
def get_settings(db: Session = Depends(get_db_with_tenant)):
    settings = db.query(PharmacySettings).first()
    if not settings:
        return {}
    return settings

@router.put("/settings")
def update_settings(s: SettingsUpdate, db: Session = Depends(get_db_with_tenant)):
    settings = db.query(PharmacySettings).first()
    if not settings:
        settings = PharmacySettings()
        db.add(settings)
    
    if s.name is not None: settings.name = s.name
    if s.tagline is not None: settings.tagline = s.tagline
    if s.phone_no is not None: settings.phone_no = s.phone_no
    if s.license_no is not None: settings.license_no = s.license_no
    if s.address is not None: settings.address = s.address
    if s.email is not None: settings.email = s.email
    if s.logo_url is not None: settings.logo_url = s.logo_url
    if s.theme_config is not None: settings.theme_config = s.theme_config
    
    db.commit()
    return settings

@router.get("/roles", response_model=List[RoleResponse])
def list_roles(db: Session = Depends(get_db_with_tenant)):
    return db.query(Role).all()

# --- APP SETTINGS ---

class AppSettingsSchema(BaseModel):
    default_listing_rows: int | None = 10
    invoice_template_id: str | None = "default"
    invoice_custom_config: dict | None = None
    sale_module: str | None = "Default" # Default, FIFO, FEFO, Avg Cost
    stock_adj_batch_required: bool | None = False

@router.get("/app-settings")
def get_app_settings(db: Session = Depends(get_db_with_tenant)):
    settings = db.query(AppSettings).first()
    if not settings:
        # Create default if not exists
        settings = AppSettings(
            default_listing_rows=10,
            invoice_template_id="default",
            sale_module="Default",
            stock_adj_batch_required=False
        )
        db.add(settings)
        db.commit()
    return settings

@router.put("/app-settings")
def update_app_settings(s: AppSettingsSchema, db: Session = Depends(get_db_with_tenant)):
    settings = db.query(AppSettings).first()
    if not settings:
        settings = AppSettings()
        db.add(settings)
    
    if s.default_listing_rows is not None:
        settings.default_listing_rows = s.default_listing_rows
    if s.invoice_template_id is not None:
        settings.invoice_template_id = s.invoice_template_id
    if s.invoice_custom_config is not None:
        settings.invoice_custom_config = s.invoice_custom_config
    if s.sale_module is not None:
        settings.sale_module = s.sale_module
    if s.stock_adj_batch_required is not None:
        settings.stock_adj_batch_required = s.stock_adj_batch_required
    
    db.commit()
    return settings
