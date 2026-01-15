from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from sqlalchemy import func, text

from ..models import PurchaseOrder, PurchaseOrderItem, Product, Manufacturer, GRN, GRNItem
from ..schemas import (
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse, 
    POGenerateRequest, POSuggestionItem,
    GRNCreate, GRNResponse
)
from ..auth import get_db_with_tenant

router = APIRouter()

from typing import List, Optional

@router.get("/orders", response_model=List[PurchaseOrderResponse])
def list_pos(
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db_with_tenant)
):
    query = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product)
    )
    
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    if status:
        query = query.filter(PurchaseOrder.status == status)
        
    return query.order_by(PurchaseOrder.created_at.desc()).all()

@router.get("/orders/{order_id}", response_model=PurchaseOrderResponse)
def get_po(order_id: int, db: Session = Depends(get_db_with_tenant)):
    po = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product)
    ).filter(PurchaseOrder.id == order_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    return po

@router.post("/orders", response_model=PurchaseOrderResponse)
def create_po(po_in: PurchaseOrderCreate, db: Session = Depends(get_db_with_tenant)):
    try:
        # Generate PO number
        po_no = f"PO-{datetime.now().strftime('%y%m%d%H%M%S')}"
        
        db_po = PurchaseOrder(
            po_no=po_no,
            supplier_id=po_in.supplier_id,
            reference_no=po_in.reference_no,
            issue_date=po_in.issue_date,
            delivery_date=po_in.delivery_date,
            sub_total=po_in.sub_total,
            total_tax=po_in.total_tax,
            total_discount=po_in.total_discount,
            total_amount=po_in.total_amount,
            status=po_in.status,
            notes=po_in.notes
        )
        db.add(db_po)
        db.flush() # Flush to get ID
        po_id = db_po.id
        
        for item in po_in.items:
            db_item = PurchaseOrderItem(
                purchase_order_id=po_id,
                **item.dict()
            )
            db.add(db_item)
        
        db.commit() # Final commit
        # db.refresh(db_po)
        
        # Restore tenant search path
        tenant_schema = db.info.get('tenant_schema')
        if tenant_schema:
            db.execute(text(f"SET search_path TO {tenant_schema}, public"))

        db_po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        return db_po
    except Exception as e:
        import traceback
        with open("error.log", "a") as f:
            f.write(f"Error creating PO: {str(e)}\n")
            f.write(traceback.format_exc())
            f.write("\n" + "="*50 + "\n")
        raise e

@router.put("/orders/{order_id}", response_model=PurchaseOrderResponse)
def update_po(order_id: int, po_in: PurchaseOrderUpdate, db: Session = Depends(get_db_with_tenant)):
    db_po = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    update_data = po_in.dict(exclude_unset=True)
    items_data = update_data.pop('items', None)
    
    for field, value in update_data.items():
        setattr(db_po, field, value)
    
    if items_data is not None:
        # Simple approach: remove old items and add new ones
        db.query(PurchaseOrderItem).filter(PurchaseOrderItem.purchase_order_id == order_id).delete()
        for item in items_data:
            db_item = PurchaseOrderItem(
                purchase_order_id=order_id,
                **item
            )
            db.add(db_item)
            
    db.commit()
    
    # Restore tenant search path
    tenant_schema = db.info.get('tenant_schema')
    if tenant_schema:
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))

    db_po = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    return db_po

@router.delete("/orders/{order_id}")
def delete_po(order_id: int, db: Session = Depends(get_db_with_tenant)):
    db_po = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not db_po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    # Delete items first
    db.query(PurchaseOrderItem).filter(PurchaseOrderItem.purchase_order_id == order_id).delete()
    db.delete(db_po)
    db.commit()
    return {"message": "Purchase Order deleted successfully"}

@router.post("/generate", response_model=List[POSuggestionItem])
def generate_suggestions(req: POGenerateRequest, db: Session = Depends(get_db_with_tenant)):
    try:
        from ..models import StockInventory
        # Fetch products for the supplier with joinedload for efficiency
        products = db.query(Product).options(joinedload(Product.manufacturer)).filter(Product.supplier_id == req.supplier_id).all()
        suggestions = []
        
        for p in products:
            current_stock = db.query(func.sum(StockInventory.quantity)).filter(
                StockInventory.product_id == p.id,
                StockInventory.is_available == True
            ).scalar() or 0
            
            pending_qty = db.query(func.sum(PurchaseOrderItem.quantity)).join(PurchaseOrder).filter(
                PurchaseOrder.status == "Pending",
                PurchaseOrderItem.product_id == p.id
            ).scalar() or 0
            
            suggested_qty = 0
            if req.method == 'min':
                suggested_qty = max(0, (p.min_inventory_level or 0) - current_stock - pending_qty)
            elif req.method == 'optimal':
                suggested_qty = max(0, (p.optimal_inventory_level or 0) - current_stock - pending_qty)
            elif req.method == 'max':
                suggested_qty = max(0, (p.max_inventory_level or 0) - current_stock - pending_qty)
            elif req.method == 'sale' and req.sale_start_date and req.sale_end_date:
                days = (req.sale_end_date - req.sale_start_date).days or 1
                suggested_qty = max(0, (days // 2) - current_stock - pending_qty)
                
            if suggested_qty > 0 or req.method == 'none':
                suggestions.append(POSuggestionItem(
                    product_id=p.id,
                    product_name=p.product_name,
                    product_code=str(p.id), # Product code is removed, using ID as fallback
                    current_stock=current_stock,
                    suggested_qty=suggested_qty,
                    cost_price=p.average_cost or 0.0,
                    manufacturer=p.manufacturer.name if p.manufacturer else "Unknown",
                    purchase_conv_unit_id=p.purchase_conv_unit_id
                ))
                
        return suggestions
    except Exception as e:
        import traceback
        with open("error.log", "a") as f:
            f.write(f"Error generating suggestions: {str(e)}\n")
            f.write(traceback.format_exc())
            f.write("\n" + "="*50 + "\n")
        raise e

# --- GRN Routes ---

@router.post("/grn", response_model=GRNResponse)
def create_grn(grn_in: GRNCreate, db: Session = Depends(get_db_with_tenant)):
    from ..models import StockInventory
    from ..models.user_models import Store
    
    try:
        # 1. Create GRN Header
        custom_grn_no = f"GRN-{datetime.now().strftime('%y%m%d%H%M%S')}"
        
        db_grn = GRN(
            custom_grn_no=custom_grn_no,
            supplier_id=grn_in.supplier_id,
            po_id=grn_in.po_id,
            invoice_no=grn_in.invoice_no,
            invoice_date=grn_in.invoice_date,
            bill_no=grn_in.bill_no,
            bill_date=grn_in.bill_date,
            due_date=grn_in.due_date,
            payment_mode=grn_in.payment_mode,
            comments=grn_in.comments,
            sub_total=0, 
            loading_exp=grn_in.loading_exp,
            freight_exp=grn_in.freight_exp,
            other_exp=grn_in.other_exp,
            purchase_tax=grn_in.purchase_tax,
            advance_tax=grn_in.advance_tax,
            discount=grn_in.discount,
            net_total=0
        )
        db.add(db_grn)
        db.flush()
        grn_id = db_grn.id
        db.commit()
        # db.refresh(db_grn) -- REMOVED per multi-tenant best practice
        
        # Restore tenant search path
        tenant_schema = db.info.get('tenant_schema')
        if tenant_schema:
            db.execute(text(f"SET search_path TO {tenant_schema}, public"))

        db_grn = db.query(GRN).filter(GRN.id == grn_id).first()
        
        calculated_sub_total = 0.0
        
        # 2. Process Items
        for item in grn_in.items:
            # Create GRNItem
            db_item = GRNItem(
                grn_id=db_grn.id,
                **item.dict()
            )
            db.add(db_item)
            calculated_sub_total += item.total_cost
            
            # --- Inventory & Cost Logic ---
            product = db.query(Product).get(item.product_id)
            if product:
                # ✅ CREATE STOCK_INVENTORY ENTRY
                # This is now the primary inventory tracking system
                from ..models import StockInventory
                
                stock_inv = StockInventory(
                    product_id=item.product_id,
                    batch_number=item.batch_no,
                    expiry_date=item.expiry_date,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    selling_price=item.retail_price,
                    warehouse_location=None,  # Can be set later or from GRN input
                    supplier_id=grn_in.supplier_id,
                    grn_id=db_grn.id,
                    is_available=True
                )
                db.add(stock_inv)
                
                # Update Product Average Cost (Weighted Average)
                total_stock = db.query(func.sum(StockInventory.quantity)).filter(
                    StockInventory.product_id == item.product_id,
                    StockInventory.is_available == True
                ).scalar() or 0
                old_avg = product.average_cost or 0
                
                # total_stock includes current batch update? 
                # scalar() query hits DB. If we haven't committed batch update, `total_stock` is BEFORE update.
                # So we have: Old Total Value = total_stock * old_avg
                # New Value = item.total_cost (UnitCost * Qty)
                # New Qty = total_stock + item.quantity
                
                current_value = total_stock * old_avg
                new_value = item.total_cost
                new_total_qty = total_stock + item.quantity
                
                if new_total_qty > 0:
                    product.average_cost = (current_value + new_value) / new_total_qty
                
                # Update Retail Price if higher (optional logic, but standard behavior)
                if item.retail_price > (product.retail_price or 0):
                    product.retail_price = item.retail_price

        # 3. Update Financials
        db_grn.sub_total = calculated_sub_total
        db_grn.net_total = (calculated_sub_total + 
                           grn_in.loading_exp + grn_in.freight_exp + grn_in.other_exp + 
                           grn_in.purchase_tax + grn_in.advance_tax) - grn_in.discount
        
        # 4. Update PO Status
        if grn_in.po_id:
            po = db.query(PurchaseOrder).get(grn_in.po_id)
            if po:
                po.status = "Received"
        
        db.commit()
        # db.refresh(db_grn)
        
        # Restore tenant search path
        tenant_schema = db.info.get('tenant_schema')
        if tenant_schema:
            db.execute(text(f"SET search_path TO {tenant_schema}, public"))

        db_grn = db.query(GRN).filter(GRN.id == grn_id).first()
        return db_grn

    except Exception as e:
        import traceback
        with open("error.log", "a") as f:
            f.write(f"Error creating GRN: {str(e)}\\n")
            f.write(traceback.format_exc())
            f.write("\\n" + "="*50 + "\\n")
        raise e

@router.get("/grn", response_model=List[GRNResponse])
def list_grns(
    supplier_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db_with_tenant)
):
    query = db.query(GRN).options(joinedload(GRN.items))
    
    if supplier_id:
        query = query.filter(GRN.supplier_id == supplier_id)
    if start_date:
        query = query.filter(GRN.created_at >= start_date)
    if end_date:
        query = query.filter(GRN.created_at <= end_date)
        
    return query.order_by(GRN.created_at.desc()).all()
