from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
import traceback

from ..models import (
    Patient, Invoice, InvoiceItem, SalesReturn, 
    Batch, Product, RegulatoryLog, User
)
from ..schemas import InvoiceCreate
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

@router.post("/return")
def process_return(invoice_id: int, amount: float, reason: str, db: Session = Depends(get_db_with_tenant)):
    ret = SalesReturn(invoice_id=invoice_id, refund_amount=amount, reason=reason)
    db.add(ret); db.commit(); db.refresh(ret)
    return ret

@router.get("/patients/history/{patient_id}")
def patient_history(patient_id: int, db: Session = Depends(get_db_with_tenant)):
    return db.query(Invoice).filter(Invoice.patient_id == patient_id).options(joinedload(Invoice.items)).all()

# Invoice creation is at root level /invoices for compatibility
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

# Patients routes are at root level for compatibility
