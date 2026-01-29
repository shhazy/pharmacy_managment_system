from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Optional
from datetime import datetime

from ..models import StockInventory, StockAdjustment, Product
from ..services.accounting_service import AccountingService
from ..schemas.procurement_schemas import StockAdjustmentCreate, StockAdjustmentResponse
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

@router.post("/adjust", response_model=StockAdjustmentResponse)
def adjust_inventory(adj_in: StockAdjustmentCreate, db: Session = Depends(get_db_with_tenant), user=Depends(get_current_tenant_user)):
    # 1. Validate Target (Inventory ID or Product+Batch)
    stock = None
    if adj_in.inventory_id:
        stock = db.query(StockInventory).filter(StockInventory.inventory_id == adj_in.inventory_id).first()
    elif adj_in.product_id and adj_in.batch_number:
        stock = db.query(StockInventory).filter(
            StockInventory.product_id == adj_in.product_id,
            StockInventory.batch_number == adj_in.batch_number,
            StockInventory.is_available == True
        ).first()
    
    if not stock:
        raise HTTPException(status_code=404, detail="Stock inventory not found for given criteria")

    # 2. Record Adjustment
    previous_qty = stock.quantity
    new_qty = previous_qty + adj_in.quantity_adjusted
    
    if new_qty < 0:
        raise HTTPException(status_code=400, detail=f"Adjustment would result in negative stock ({new_qty})")

    db_adj = StockAdjustment(
        product_id=adj_in.product_id,
        inventory_id=stock.inventory_id,
        batch_number=adj_in.batch_number or stock.batch_number,
        adjustment_type=adj_in.adjustment_type,
        quantity_adjusted=adj_in.quantity_adjusted,
        previous_quantity=previous_qty,
        new_quantity=new_qty,
        reason=adj_in.reason,
        reference_number=adj_in.reference_number,
        adjusted_by=user.id,
        status="approved" # Auto-approving for now as per simple flow
    )
    db.add(db_adj)
    db.flush() # Get adjustment_id
    
    # Process Stock Update
    stock.quantity = new_qty
    if new_qty == 0:
        stock.is_available = False # Optionally mark as unavailable if zero

    db.commit()
    
    # --- Accounting Integration ---
    if db_adj.adjustment_type == "return_to_supplier":
        try:
            AccountingService.record_inventory_adjustment_accounting(db, db_adj, user.id)
        except Exception as e:
            # We don't want to fail the inventory save if accounting fails, 
            # but we should log it. In production, consider a background task or more robust retry.
            print(f"ACCOUNTING ERROR during return: {e}")
            import traceback
            traceback.print_exc()

    # Pattern from product_routes.py: Explicitly restore search_path after commit 
    # to avoid search_path loss during reconnection/refresh.
    tenant_schema = db.info.get('tenant_schema')
    if tenant_schema:
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))
    
    # Re-fetch the object to ensure it's fully populated and visible
    db_adj = db.query(StockAdjustment).filter(StockAdjustment.adjustment_id == db_adj.adjustment_id).first()
    return db_adj

@router.get("/adjustments", response_model=List[StockAdjustmentResponse])
def list_adjustments(db: Session = Depends(get_db_with_tenant), user=Depends(get_current_tenant_user)):
    return db.query(StockAdjustment).order_by(StockAdjustment.adjustment_date.desc()).all()
