from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
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
    db.add(ret)
    db.flush()
    ret_id = ret.id
    db.commit()
    # db.refresh(ret)
    
    # Restore tenant search path
    tenant_schema = db.info.get('tenant_schema')
    if tenant_schema:
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))

    ret = db.query(SalesReturn).filter(SalesReturn.id == ret_id).first()
    return ret

@router.get("/patients/history/{patient_id}")
def patient_history(patient_id: int, db: Session = Depends(get_db_with_tenant)):
    return db.query(Invoice).filter(Invoice.patient_id == patient_id).options(joinedload(Invoice.items)).all()

# Note: Removed broken copy-pasted invoice creation code that was here.

# Patients routes are at root level for compatibility
