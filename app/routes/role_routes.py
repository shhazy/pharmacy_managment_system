from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from ..models import Role, Permission
from ..schemas import RoleResponse, RoleCreate, RoleUpdate, PermissionResponse
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

@router.get("", response_model=List[RoleResponse])
def list_roles(db: Session = Depends(get_db_with_tenant), user=Depends(get_current_tenant_user)):
    return db.query(Role).all()

@router.post("", response_model=RoleResponse)
def create_role(role_in: RoleCreate, db: Session = Depends(get_db_with_tenant), user=Depends(get_current_tenant_user)):
    existing = db.query(Role).filter(func.lower(Role.name) == role_in.name.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role with this name already exists")
    
    new_role = Role(name=role_in.name, description=role_in.description)
    
    # Add permissions
    if role_in.permission_ids:
        perms = db.query(Permission).filter(Permission.id.in_(role_in.permission_ids)).all()
        new_role.permissions = perms
        
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role

@router.put("/{id}", response_model=RoleResponse)
def update_role(id: int, role_in: RoleUpdate, db: Session = Depends(get_db_with_tenant), user=Depends(get_current_tenant_user)):
    role = db.query(Role).filter(Role.id == id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.name in ["Admin", "Manager", "Pharmacist", "Cashier"] and role_in.name and role_in.name != role.name:
         # Prevent renaming system roles if desired, or skip
         pass

    if role_in.name:
        role.name = role_in.name
    if role_in.description is not None:
        role.description = role_in.description
        
    if role_in.permission_ids is not None:
        perms = db.query(Permission).filter(Permission.id.in_(role_in.permission_ids)).all()
        role.permissions = perms
        
    db.commit()
    db.refresh(role)
    return role

@router.delete("/{id}")
def delete_role(id: int, db: Session = Depends(get_db_with_tenant), user=Depends(get_current_tenant_user)):
    role = db.query(Role).filter(Role.id == id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.name in ["Admin", "Manager"]:
        raise HTTPException(status_code=400, detail="Cannot delete system critical roles")

    db.delete(role)
    db.commit()
    return {"message": "Role deleted successfully"}
