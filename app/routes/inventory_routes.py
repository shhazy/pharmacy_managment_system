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
    
    from ..models.pharmacy_models import AppSettings
    app_settings = db.query(AppSettings).first()
    sale_module = app_settings.sale_module if app_settings else "FIFO"

    response = []
    for p, cat_name, gen_name in results:
        # Aggregate stock info
        available_stock = [s for s in p.stock_inventory if s.is_available]
        
        # Sort based on sale_module setting
        if sale_module == "FEFO":
            available_stock.sort(key=lambda x: (x.expiry_date is None, x.expiry_date))
        else: # FIFO and Avg Cost
            available_stock.sort(key=lambda x: x.inventory_id)
            
        total_stock = sum(s.quantity for s in available_stock)
        
        # Get latest batch info for price and expiry (based on current selection method)
        latest_inv = available_stock # Already sorted correctly
        
        p_dict = {
            "id": p.id,
            "product_name": p.product_name,
            "name": p.product_name, # Alias for compatibility
            "generic_name": gen_name or "N/A",
            "category": cat_name or "Uncategorized",
            "supplier_id": p.supplier_id,
            "product_suppliers": [{"supplier_id": ps.supplier_id} for ps in p.product_suppliers],
            "manufacturer_id": p.manufacturer_id,
            "base_unit_id": p.base_unit_id,
            "purchase_conv_unit_id": p.purchase_conv_unit_id,
            "purchase_conv_factor": p.purchase_conv_factor,
            "preferred_purchase_unit_id": p.preferred_purchase_unit_id,
            "preferred_pos_unit_id": p.preferred_pos_unit_id,
            "average_cost": p.average_cost,
            "retail_price": p.retail_price,
            "tax_percent": p.tax_percent or 0,
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
                    "tax_percent": s.tax_percent or 0,
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

@router.get("/stock-summary")
def get_stock_summary(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    """Return products with aggregated stock quantities."""
    results = db.query(
        Product.id,
        Product.product_name,
        Product.purchase_conv_factor,
        func.sum(StockInventory.quantity).label("total_quantity"),
        func.max(StockInventory.created_at).label("latest_created")
    ).join(StockInventory, Product.id == StockInventory.product_id)\
     .filter(StockInventory.is_available == True)\
     .group_by(Product.id, Product.product_name, Product.purchase_conv_factor)\
     .all()
    
    response = []
    for pid, name, factor, total_qty, latest_created in results:
        # Get latest batch info for basic display (price, etc.)
        latest_batch = db.query(StockInventory).filter(
            StockInventory.product_id == pid,
            StockInventory.is_available == True
        ).order_by(StockInventory.inventory_id.desc()).first()

        response.append({
            "product_id": pid,
            "product_name": name,
            "total_quantity": total_qty,
            "purchase_conv_factor": factor or 1,
            "latest_batch": {
                "inventory_id": latest_batch.inventory_id,
                "batch_number": latest_batch.batch_number,
                "expiry_date": latest_batch.expiry_date.isoformat() if latest_batch.expiry_date else None,
                "selling_price": latest_batch.selling_price,
                "unit_cost": latest_batch.unit_cost,
                "supplier_name": latest_batch.supplier.name if latest_batch.supplier else "N/A"
            } if latest_batch else None
        })
    return response

@router.get("/product/{product_id}/batches")
def get_product_batches(product_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    """Return all batches for a specific product."""
    batches = db.query(StockInventory).options(
        joinedload(StockInventory.supplier),
        joinedload(StockInventory.product)
    ).filter(
        StockInventory.product_id == product_id,
        StockInventory.is_available == True
    ).order_by(StockInventory.inventory_id.desc()).all()
    
    return [{
        "inventory_id": b.inventory_id,
        "batch_number": b.batch_number,
        "expiry_date": b.expiry_date.isoformat() if b.expiry_date else None,
        "quantity": b.quantity,
        "unit_cost": b.unit_cost,
        "selling_price": b.selling_price,
        "supplier_name": b.supplier.name if b.supplier else "N/A",
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "purchase_conv_factor": b.product.purchase_conv_factor if b.product else 1
    } for b in batches]

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
