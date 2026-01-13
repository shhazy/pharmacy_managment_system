from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import traceback

from ..database import get_db
from ..models import Tenant, User, SuperAdmin
from ..schemas import Token, LoginRequest
from ..auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_superadmin,
    get_current_tenant_user,
    get_current_user_data
)

router = APIRouter()

@router.post("/auth/login/", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    try:
        if login_data.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.subdomain == login_data.tenant_id).first()
            if not tenant: raise HTTPException(status_code=404, detail="Pharmacy not found")
            
            db.execute(text(f"SET search_path TO {tenant.schema_name}, public"))
            user = db.query(User).filter(User.username == login_data.username).first()
            
            if not user or not verify_password(login_data.password, user.hashed_password):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            access_token = create_access_token(data={
                "sub": user.username, 
                "id": user.id,
                "tenant_id": login_data.tenant_id,
                "schema_name": tenant.schema_name,
                "roles": [r.name for r in user.roles],
                "is_superadmin": False
            })
        else:
            # Superadmin Login
            db.execute(text("SET search_path TO public"))
            admin = db.query(SuperAdmin).filter(SuperAdmin.username == login_data.username).first()
            
            if not admin or not verify_password(login_data.password, admin.hashed_password):
                raise HTTPException(status_code=401, detail="Invalid admin credentials")
            
            access_token = create_access_token(data={
                "sub": admin.username,
                "id": admin.id,
                "is_superadmin": True
            })
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        traceback.print_exc()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail=f"Login Failed: {str(e)}")
