from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import SuperAdmin, Tenant, SoftwarePayment
from ..schemas.superadmin_schemas import SuperAdminResponse, SuperAdminUpdate
from ..auth import get_current_superadmin, get_password_hash

router = APIRouter()

@router.get("/me", response_model=SuperAdminResponse)
def get_me(current_admin: SuperAdmin = Depends(get_current_superadmin)):
    return current_admin

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_superadmin)
):
    total_tenants = db.query(Tenant).count()
    active_tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
    
    pending_payments = db.query(SoftwarePayment).filter(SoftwarePayment.status == 'pending').count()
    total_payments = db.query(SoftwarePayment).count()
    
    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "pending_payments": pending_payments,
        "total_payments": total_payments
    }

@router.patch("/me", response_model=SuperAdminResponse)
def update_me(
    update_data: SuperAdminUpdate,
    db: Session = Depends(get_db),
    current_admin: SuperAdmin = Depends(get_current_superadmin)
):
    if update_data.username:
        # Check if username already exists
        existing = db.query(SuperAdmin).filter(SuperAdmin.username == update_data.username).first()
        if existing and existing.id != current_admin.id:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_admin.username = update_data.username
    
    if update_data.email:
        # Check if email already exists
        existing = db.query(SuperAdmin).filter(SuperAdmin.email == update_data.email).first()
        if existing and existing.id != current_admin.id:
            raise HTTPException(status_code=400, detail="Email already taken")
        current_admin.email = update_data.email
    
    if update_data.password:
        current_admin.hashed_password = get_password_hash(update_data.password)
    
    db.commit()
    db.refresh(current_admin)
    return current_admin
