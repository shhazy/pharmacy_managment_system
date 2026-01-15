# Common routes that are at root level for backward compatibility
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload

from ..models import Category, Manufacturer, Store, Supplier, Patient, Invoice, StockInventory, Product, InvoiceItem, RegulatoryLog, User
from ..schemas import InvoiceCreate
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
            disc = line_total * (item.discount_percent / 100)
            
            sub_total += line_total
            tax_total += tax
            
            invoice_items.append(InvoiceItem(
                medicine_id=item.medicine_id, 
                batch_id=item.batch_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=(line_total + tax - disc)
            ))
            
            med = db.query(Product).get(item.medicine_id)
            if med.is_narcotic:
                db.add(RegulatoryLog(medicine_id=med.id, action="Dispensed", quantity=item.quantity, patient_id=inv_in.patient_id))

        net_total = sub_total + tax_total - inv_in.discount_amount
        
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
            status="Paid",
            payment_method=inv_in.payment_method,
            items=invoice_items
        )
        db.add(new_inv)
        db.flush()
        new_inv_id = new_inv.id
        db.commit()
        # db.refresh(new_inv)
        
        # Restore tenant search path
        tenant_schema = db.info.get('tenant_schema')
        if tenant_schema:
            db.execute(text(f"SET search_path TO {tenant_schema}, public"))

        new_inv = db.query(Invoice).filter(Invoice.id == new_inv_id).first()
        return new_inv
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
