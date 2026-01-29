from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from ..models.pharmacy_models import Product, Category, Manufacturer, Supplier
from ..models.inventory_models import Generic
from ..models.procurement_models import StockInventory
from ..models.user_models import User
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

@router.get("/")
def get_inventory(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    # Robust query using explicit join for category and generic to avoid relationship issues
    results = db.query(
        Product, 
        Category.name.label("cat_name"), 
        Generic.name.label("gen_name")
    ).outerjoin(Category, Product.category_id == Category.id)\
     .outerjoin(Generic, Product.generics_id == Generic.id)\
     .options(joinedload(Product.stock_inventory), joinedload(Product.product_suppliers))\
     .all()
    
    response = []
    for p, cat_name, gen_name in results:
        # Aggregate stock info
        available_stock = [s for s in p.stock_inventory if s.is_available]
        total_stock = sum(s.quantity for s in available_stock)
        
        # Get latest batch info for price and expiry
        latest_inv = sorted(available_stock, key=lambda x: x.expiry_date or datetime.max)
        
        p_dict = {
            "id": p.id,
            "product_name": p.product_name,
            "name": p.product_name, # Alias for compatibility
            "generic_name": gen_name or "N/A",
            "category": cat_name or "Uncategorized",
            "supplier_id": p.supplier_id,
            "product_suppliers": [{"supplier_id": ps.supplier_id} for ps in p.product_suppliers],
            "manufacturer_id": p.manufacturer_id,
            "purchase_conv_unit_id": p.purchase_conv_unit_id,
            "purchase_conv_factor": p.purchase_conv_factor,
            "preferred_purchase_unit_id": p.preferred_purchase_unit_id,
            "preferred_pos_unit_id": p.preferred_pos_unit_id,
            "average_cost": p.average_cost,
            "retail_price": p.retail_price,
            "control_drug": p.control_drug,
            "min_inventory_level": p.min_inventory_level,
            "optimal_inventory_level": p.optimal_inventory_level,
            "max_inventory_level": p.max_inventory_level,
            "stock_quantity": total_stock,
            "price": latest_inv[0].selling_price if latest_inv else 0,
            "expiry_date": latest_inv[0].expiry_date.isoformat() if latest_inv and latest_inv[0].expiry_date else None,
            "stock_inventory": [
                {
                    "inventory_id": s.inventory_id,
                    "id": s.inventory_id,
                    "batch_number": s.batch_number,
                    "quantity": s.quantity,
                    "selling_price": s.selling_price,
                    "expiry_date": s.expiry_date.isoformat() if s.expiry_date else None
                } for s in available_stock
            ]
        }
        response.append(p_dict)
    return response


@router.get("/stock")
def get_stock_list(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    """Return all stock inventory entries with product and supplier details."""
    results = db.query(StockInventory).options(
        joinedload(StockInventory.product),
        joinedload(StockInventory.supplier)
    ).filter(StockInventory.is_available == True).all()
    
    response = []
    for s in results:
        p = s.product
        response.append({
            "inventory_id": s.inventory_id,
            "product_name": p.product_name if p else "N/A",
            "batch_number": s.batch_number,
            "expiry_date": s.expiry_date.isoformat() if s.expiry_date else None,
            "quantity": s.quantity,
            "purchase_conv_factor": p.purchase_conv_factor if p else 1,
            "unit_cost": s.unit_cost,
            "selling_price": s.selling_price,
            "supplier_name": s.supplier.name if s.supplier else "N/A",
            "supplier_id": s.supplier_id,
            "product_id": s.product_id,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })
    return response

@router.patch("/stock/{inventory_id}")
def update_stock_price(inventory_id: int, selling_price: float = None, unit_cost: float = None, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    """Update prices for a specific stock inventory entry."""
    stock = db.query(StockInventory).filter(StockInventory.inventory_id == inventory_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    if selling_price is not None:
        stock.selling_price = selling_price
    if unit_cost is not None:
        stock.unit_cost = unit_cost
        
    db.commit()
    return {"status": "ok", "message": "Price updated successfully"}
