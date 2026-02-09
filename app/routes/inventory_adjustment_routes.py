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
    # 1. Fetch Settings
    from ..models.pharmacy_models import AppSettings
    settings = db.query(AppSettings).first()
    batch_required = settings.stock_adj_batch_required if settings else False

    # 2. Validate Target
    if batch_required and not adj_in.inventory_id and not adj_in.batch_number:
        raise HTTPException(status_code=400, detail="Batch number is required for stock adjustment as per app settings.")

    # 3. Handle Adjustment Logic
    remaining_to_adjust = adj_in.quantity_adjusted
    
    # We will target specific batch if provided, otherwise we iterate through latest batches
    if adj_in.inventory_id or adj_in.batch_number:
        stock = None
        if adj_in.inventory_id:
            stock = db.query(StockInventory).filter(StockInventory.inventory_id == adj_in.inventory_id).first()
        else:
            stock = db.query(StockInventory).filter(
                StockInventory.product_id == adj_in.product_id,
                StockInventory.batch_number == adj_in.batch_number
            ).order_by(StockInventory.inventory_id.desc()).first()
        
        if not stock:
            raise HTTPException(status_code=404, detail="Selected batch not found.")
        
        batches = [stock]
    else:
        # No batch specified, find latest available batches
        batches = db.query(StockInventory).filter(
            StockInventory.product_id == adj_in.product_id,
            StockInventory.is_available == True
        ).order_by(StockInventory.inventory_id.desc()).all()
        
        if not batches:
            # Try to find even unavailable batches if it's a positive adjustment
            if remaining_to_adjust > 0:
                batches = db.query(StockInventory).filter(
                    StockInventory.product_id == adj_in.product_id
                ).order_by(StockInventory.inventory_id.desc()).limit(1).all()
            
            if not batches:
                raise HTTPException(status_code=404, detail="No batches found for this product. Please ensure the product has at least one batch history.")

    # Process adjustments
    last_adj = None
    applied_to_any = False

    for batch in batches:
        if remaining_to_adjust == 0:
            break
            
        previous_qty = batch.quantity
        adjustment_for_this_batch = 0
        
        if remaining_to_adjust > 0:
            # Positive adjustment: just add everything to the latest (first) batch
            adjustment_for_this_batch = remaining_to_adjust
            remaining_to_adjust = 0
        else:
            # Negative adjustment: subtract from this batch up to its available quantity
            can_subtract = batch.quantity
            if abs(remaining_to_adjust) <= can_subtract:
                adjustment_for_this_batch = remaining_to_adjust
                remaining_to_adjust = 0
            else:
                # Subtract everything from this batch and move to next
                adjustment_for_this_batch = -can_subtract
                remaining_to_adjust += can_subtract
        
        if adjustment_for_this_batch == 0:
            continue
            
        new_qty = previous_qty + adjustment_for_this_batch
        
        db_adj = StockAdjustment(
            product_id=adj_in.product_id,
            inventory_id=batch.inventory_id,
            batch_number=batch.batch_number,
            adjustment_type=adj_in.adjustment_type,
            quantity_adjusted=adjustment_for_this_batch,
            previous_quantity=previous_qty,
            new_quantity=new_qty,
            reason=adj_in.reason,
            reference_number=adj_in.reference_number,
            adjusted_by=user.id,
            status="approved"
        )
        db.add(db_adj)
        
        batch.quantity = new_qty
        if new_qty <= 0:
            batch.is_available = False
        else:
            batch.is_available = True
            
        last_adj = db_adj
        applied_to_any = True

    if not applied_to_any and adj_in.quantity_adjusted != 0:
         raise HTTPException(status_code=400, detail="Could not apply adjustment. Check stock availability.")

    if remaining_to_adjust != 0 and adj_in.quantity_adjusted < 0:
        # If we still have negative adjustment left, it means total stock was insufficient
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Insufficient total stock. Could not adjust remaining {abs(remaining_to_adjust)} units.")

    db.commit()
    
    # --- Accounting Integration ---
    if last_adj.adjustment_type == "return_to_supplier":
        try:
            AccountingService.record_inventory_adjustment_accounting(db, last_adj, user.id)
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
    last_adj = db.query(StockAdjustment).filter(StockAdjustment.adjustment_id == last_adj.adjustment_id).first()
    return last_adj

@router.get("/adjustments", response_model=List[StockAdjustmentResponse])
def list_adjustments(db: Session = Depends(get_db_with_tenant), user=Depends(get_current_tenant_user)):
    return db.query(StockAdjustment).order_by(StockAdjustment.adjustment_date.desc()).all()
