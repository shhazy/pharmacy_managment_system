from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from ..models import Permission
from ..schemas import PermissionResponse
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

@router.get("", response_model=List[PermissionResponse])
def list_permissions(db: Session = Depends(get_db_with_tenant), user=Depends(get_current_tenant_user)):
    return db.query(Permission).order_by(Permission.module, Permission.name).all()
