# Common routes that are at root level for backward compatibility
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload

from ..models import Category, Manufacturer, Store, Supplier, Patient, Invoice, Batch, Product, InvoiceItem, RegulatoryLog, User
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
    db.add(store); db.commit(); db.refresh(store)
    return store

# Suppliers (at root for compatibility)
@router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db_with_tenant)):
    return db.query(Supplier).all()

@router.post("/suppliers")
def add_supplier(name: str, address: str, gst: str, db: Session = Depends(get_db_with_tenant)):
    sup = Supplier(name=name, address=address, gst_number=gst)
    db.add(sup); db.commit(); db.refresh(sup)
    return sup

# Patients (at root for compatibility)
@router.get("/patients")
def list_patients(db: Session = Depends(get_db_with_tenant)):
    return db.query(Patient).all()

@router.post("/patients")
def add_patient(p_name: str, p_phone: str, db: Session = Depends(get_db_with_tenant)):
    p = Patient(name=p_name, phone=p_phone)
    db.add(p); db.commit(); db.refresh(p)
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
            batch = db.query(Batch).filter(Batch.id == item.batch_id, Batch.product_id == item.medicine_id).first()
            if not batch or batch.current_stock < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {item.medicine_id} batch {item.batch_id}")
            
            batch.current_stock -= item.quantity
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
        db.add(new_inv); db.commit(); db.refresh(new_inv)
        return new_inv
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

# Stock Transfer (at root for compatibility)
@router.post("/stock/transfer")
def transfer_stock(from_id: int, to_id: int, med_id: int, qty: int, db: Session = Depends(get_db_with_tenant)):
    from fastapi import HTTPException
    from ..models import StockTransfer
    
    batch = db.query(Batch).filter(Batch.product_id == med_id, Batch.store_id == from_id).first()
    if not batch or batch.current_stock < qty:
        raise HTTPException(status_code=400, detail="Insufficient stock at source branch")
    
    batch.current_stock -= qty
    transfer = StockTransfer(from_store_id=from_id, to_store_id=to_id, medicine_id=med_id, quantity=qty)
    db.add(transfer); db.commit()
    return {"message": "Transfer initiated"}

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
    return db.query(Batch).join(Medicine).filter(Batch.expiry_date <= next_90_days, Batch.current_stock > 0).all()

@router.get("/reports/low-stock")
def get_low_stock(db: Session = Depends(get_db_with_tenant)):
    return db.query(Product).join(Batch).group_by(Product.id).having(func.sum(Batch.current_stock) <= Product.reorder_level).all()
