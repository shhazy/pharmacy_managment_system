from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from typing import List

from ..models import Category, Manufacturer, Store, Supplier, Patient, Invoice, StockInventory, Product, InvoiceItem, RegulatoryLog, User, Role
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
            
            # Item level discount: handle both % and Value modes
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
                total_price=item_net
            ))
            
            med = db.query(Product).get(item.medicine_id)
            if med.control_drug:
                db.add(RegulatoryLog(medicine_id=med.id, action="Dispensed", quantity=item.quantity, patient_id=inv_in.patient_id))

        # Net total is the sum of items' net prices minus the global invoice discount (adjustment)
        items_net_sum = sum(it.total_price for it in invoice_items)
        net_total = items_net_sum - inv_in.discount_amount
        
        new_inv = Invoice(
            invoice_number=f"INV-{datetime.now().strftime('%y%m%d%H%M%S')}",
            patient_id=inv_in.patient_id,
            user_id=user.id,
            store_id=user.store_id,
            sub_total=sub_total,
            tax_amount=tax_total,
            discount_amount=inv_in.discount_amount,
            net_total=net_total,
            paid_amount=net_total,
            status=inv_in.status,
            payment_method=inv_in.payment_method,
            items=invoice_items
        )
        db.add(new_inv)
        db.flush()
        new_inv_id = new_inv.id
        db.commit()
        
        # Restore tenant search path
        tenant_schema = db.info.get('tenant_schema')
        if tenant_schema:
            db.execute(text(f"SET search_path TO {tenant_schema}, public"))

        new_inv = db.query(Invoice).filter(Invoice.id == new_inv_id).first()
        
        # Create accounting entry if Paid or Return
        if inv_in.status in ["Paid", "Return"]:
            try:
                from ..services.accounting_service import AccountingService
                
                if inv_in.status == "Paid":
                    AccountingService.record_sale_transaction(db, new_inv, user.id)
                elif inv_in.status == "Return":
                    AccountingService.record_return_transaction(db, new_inv, user.id)
                
                print(f"✓ Accounting entry created for invoice {new_inv.invoice_number}")
            except Exception as acc_err:
                # Log but don't fail the invoice creation
                print(f"⚠ Warning: Failed to create accounting entry: {acc_err}")
                traceback.print_exc()
        
        return new_inv
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
        
    return query.order_by(Invoice.created_at.desc()).limit(limit).options(joinedload(Invoice.items).joinedload(InvoiceItem.product)).all()

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
