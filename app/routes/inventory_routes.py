from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from ..models import Product, Category, Manufacturer, User
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

@router.get("/")
def get_inventory(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    return db.query(Product).options(joinedload(Product.batches)).all()

# Categories and manufacturers are at root level for compatibility
