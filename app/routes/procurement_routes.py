from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..models import Store, Supplier, PurchaseOrder, StockTransfer, Batch
from ..auth import get_db_with_tenant

router = APIRouter()

# Stores and suppliers routes are at root level for compatibility

@router.get("/orders")
def list_pos(db: Session = Depends(get_db_with_tenant)):
    return db.query(PurchaseOrder).all()

@router.post("/orders")
def create_po(supplier_id: int, amount: float, db: Session = Depends(get_db_with_tenant)):
    po = PurchaseOrder(supplier_id=supplier_id, total_amount=amount)
    db.add(po); db.commit(); db.refresh(po)
    return po

# Stock transfer is at root level /stock/transfer for compatibility
