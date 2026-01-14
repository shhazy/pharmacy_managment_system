from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models import User, Role
from ..schemas import UserCreate, UserUpdate, UserResponse, RoleResponse
from ..auth import get_db_with_tenant, get_current_tenant_user, get_password_hash

router = APIRouter()

@router.get("", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    return db.query(User).all()

@router.post("", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db_with_tenant), current_user: User = Depends(get_current_tenant_user)):
    roles = db.query(Role).filter(Role.name.in_(user_in.role_names)).all()
    new_u = User(username=user_in.username, email=user_in.email, hashed_password=get_password_hash(user_in.password), roles=roles)
    db.add(new_u)
    db.flush()
    new_u_id = new_u.id
    db.commit()
    # db.refresh(new_u) -- REMOVED per multi-tenant best practice
    
    # Restore tenant search path
    tenant_schema = db.info.get('tenant_schema')
    if tenant_schema:
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))

    new_u = db.query(User).filter(User.id == new_u_id).first()
    return new_u

@router.get("/roles", response_model=List[RoleResponse])
def list_roles(db: Session = Depends(get_db_with_tenant)):
    return db.query(Role).all()
