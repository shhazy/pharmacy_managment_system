from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
from datetime import datetime

from ..database import get_db
from ..models import SoftwarePayment, SuperAdmin, Tenant
from ..schemas import SoftwarePaymentResponse, SoftwarePaymentUpdate
from ..auth import get_current_superadmin, get_current_user_data as get_current_user

router = APIRouter()

# Directory for receipts
UPLOAD_DIR = "uploads/receipts"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/", response_model=SoftwarePaymentResponse)
async def submit_payment(
    valid_from: datetime = Form(...),
    valid_to: datetime = Form(...),
    receipt: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Determine tenant_id from current_user
    tenant_subdomain = current_user.get("tenant_id")
    if not tenant_subdomain:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")
    
    tenant = db.query(Tenant).filter(Tenant.subdomain == tenant_subdomain).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant_id = tenant.id

    file_ext = os.path.splitext(receipt.filename)[1]
    file_name = f"receipt_{tenant_id}_{datetime.now().timestamp()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(receipt.file, buffer)

    db_payment = SoftwarePayment(
        tenant_id=tenant_id,
        receipt_path=file_path,
        valid_from=valid_from,
        valid_to=valid_to,
        status="pending"
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

@router.put("/{payment_id}", response_model=SoftwarePaymentResponse)
async def update_my_payment(
    payment_id: int,
    valid_from: datetime = Form(...),
    valid_to: datetime = Form(...),
    receipt: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Verify tenant
    tenant_subdomain = current_user.get("tenant_id")
    if not tenant_subdomain:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")
    
    tenant = db.query(Tenant).filter(Tenant.subdomain == tenant_subdomain).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    db_payment = db.query(SoftwarePayment).filter(
        SoftwarePayment.id == payment_id,
        SoftwarePayment.tenant_id == tenant.id
    ).first()

    if not db_payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if db_payment.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending payments can be updated")

    db_payment.valid_from = valid_from
    db_payment.valid_to = valid_to

    if receipt:
        file_ext = os.path.splitext(receipt.filename)[1]
        file_name = f"receipt_{tenant.id}_{datetime.now().timestamp()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(receipt.file, buffer)
        
        db_payment.receipt_path = file_path

    db.commit()
    db.refresh(db_payment)
    return db_payment

@router.get("/my", response_model=List[SoftwarePaymentResponse])
def get_my_payments(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    tenant_subdomain = current_user.get("tenant_id")
    if not tenant_subdomain:
        raise HTTPException(status_code=400, detail="User not associated with a tenant")
    
    tenant = db.query(Tenant).filter(Tenant.subdomain == tenant_subdomain).first()
    if not tenant:
        return []

    return db.query(SoftwarePayment).filter(SoftwarePayment.tenant_id == tenant.id).all()

@router.get("/all", response_model=List[SoftwarePaymentResponse])
def get_all_payments(
    db: Session = Depends(get_db),
    admin: SuperAdmin = Depends(get_current_superadmin)
):
    return db.query(SoftwarePayment).all()

@router.patch("/{payment_id}/status", response_model=SoftwarePaymentResponse)
def update_payment_status(
    payment_id: int,
    update: SoftwarePaymentUpdate,
    db: Session = Depends(get_db),
    admin: SuperAdmin = Depends(get_current_superadmin)
):
    db_payment = db.query(SoftwarePayment).filter(SoftwarePayment.id == payment_id).first()
    if not db_payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    db_payment.status = update.status
    if update.rejection_reason:
        db_payment.rejection_reason = update.rejection_reason
    
    if update.valid_from:
        db_payment.valid_from = update.valid_from
    if update.valid_to:
        db_payment.valid_to = update.valid_to
    
    db.commit()
    db.refresh(db_payment)
    return db_payment
