from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, func

from ..models import Product, ProductIngredient, ProductSupplier, ProductHistory, StockInventory, User
from ..schemas import MedicineCreate
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

@router.get("/search")
def search_products(q: str, db: Session = Depends(get_db_with_tenant)):
    from sqlalchemy import or_, func
    from sqlalchemy.orm import joinedload, aliased
    from ..models.procurement_models import StockInventory
    from ..models.pharmacy_models import Product, Category, Manufacturer
    from ..models.inventory_models import Generic, PurchaseConversionUnit
    
    # Aliases for different unit joins
    PurchaseUnit = aliased(PurchaseConversionUnit)
    PosUnit = aliased(PurchaseConversionUnit)

    results = db.query(
            Product, 
            func.sum(StockInventory.quantity).label("current_stock"),
            Category.name.label("category_name"),
            Manufacturer.name.label("manufacturer_name"),
            Generic.name.label("generic_name"),
            PurchaseUnit.name.label("purchase_unit_name"),
            PosUnit.name.label("pos_unit_name")
        )\
        .outerjoin(StockInventory, Product.id == StockInventory.product_id)\
        .outerjoin(Category, Product.category_id == Category.id)\
        .outerjoin(Manufacturer, Product.manufacturer_id == Manufacturer.id)\
        .outerjoin(Generic, Product.generics_id == Generic.id)\
        .outerjoin(PurchaseUnit, Product.purchase_conv_unit_id == PurchaseUnit.id)\
        .outerjoin(PosUnit, Product.preferred_pos_unit_id == PosUnit.id)\
        .options(joinedload(Product.stock_inventory))\
        .filter(
            or_(
                Product.product_name.ilike(f"%{q}%")
            )
        )\
        .group_by(Product.id, Category.name, Manufacturer.name, Generic.name, PurchaseUnit.name, PosUnit.name)\
        .all()
    
    from ..models.pharmacy_models import AppSettings
    app_settings = db.query(AppSettings).first()
    sale_module = app_settings.sale_module if app_settings else "FIFO"

    # Map to list of dicts or enhanced objects
    response = []
    for product, stock, cat_name, man_name, gen_name, p_unit_name, pos_unit_name in results:
        
        # Sort stock inventory based on setting
        available_batches = [s for s in product.stock_inventory if s.is_available]
        if sale_module == "FEFO":
            available_batches.sort(key=lambda x: (x.expiry_date is None, x.expiry_date))
        else: # FIFO and Avg Cost
            available_batches.sort(key=lambda x: x.inventory_id)

        p_dict = {
            "id": product.id,
            "product_name": product.product_name,
            "name": product.product_name, # Alias for compatibility
            "generic_name": gen_name or "N/A",
            "retail_price": product.retail_price,
            "current_stock": stock or 0,
            "supplier_id": product.supplier_id,
            "manufacturer_id": product.manufacturer_id,
            "category": {"id": product.category_id, "name": cat_name or "Uncategorized"},
            "manufacturer": {"id": product.manufacturer_id, "name": man_name or "N/A"},
            "tax_percent": product.tax_percent or 0,
            "uom": pos_unit_name or "Unit", # Base unit name from POS Unit
            "purchase_conv_unit_id": product.purchase_conv_unit_id,
            "purchase_conv_unit_name": p_unit_name, # Also providing this if needed
            "purchase_conv_factor": product.purchase_conv_factor,
            "preferred_purchase_unit_id": product.preferred_purchase_unit_id,
            "stock_inventory": [
                {
                    "inventory_id": s.inventory_id,
                    "id": s.inventory_id, # Alias for compatibility
                    "batch_number": s.batch_number,
                    "quantity": s.quantity,
                    "selling_price": s.selling_price,
                    "retail_price": s.retail_price,
                    "tax_percent": s.tax_percent,
                    "expiry_date": s.expiry_date.isoformat() if s.expiry_date else None
                } for s in available_batches
            ]
        }
        response.append(p_dict)
    return response

@router.get("/{id}")
def get_product_details(id: int, db: Session = Depends(get_db_with_tenant)):
    product = db.query(Product).options(
        joinedload(Product.ingredients),
        joinedload(Product.product_suppliers),
        joinedload(Product.history)
    ).filter(Product.id == id).first()
    if not product: raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/")
def add_product(med: MedicineCreate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    # Manual uniqueness check (trimmed and case-insensitive)
    name_val = med.name or med.product_name if hasattr(med, 'product_name') else med.name
    name_clean = name_val.strip()
    
    existing = db.query(Product).filter(func.lower(func.trim(Product.product_name)) == name_clean.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with name '{name_clean}' already exists.")

    # 1. Creation
    new_m = Product(
        product_name=name_clean,
        category_id=med.category_id, 
        sub_category_id=getattr(med, 'sub_category_id', None),
        product_group_id=getattr(med, 'product_group_id', None),
        category_group_id=getattr(med, 'category_group_id', None),
        generics_id=med.generics_id if hasattr(med, 'generics_id') else getattr(med, 'category_id', None),
        manufacturer_id=med.manufacturer_id,
        rack_id=getattr(med, 'rack_id', None),
        supplier_id=getattr(med, 'supplier_id', None),
        purchase_conv_unit_id=getattr(med, 'purchase_conv_unit_id', None),
        tax_percent=getattr(med, 'tax_percent', 0.0),
        product_type=getattr(med, 'product_type', 1),
        active=True
    )
    db.add(new_m); db.flush()
    
    # 2. Relations
    for ing in med.ingredients:
        db.add(ProductIngredient(product_id=new_m.id, **ing.dict()))
        
    for sup in med.suppliers:
        db.add(ProductSupplier(product_id=new_m.id, **sup.dict()))
        
    if med.batch:
        db.add(StockInventory(
            product_id=new_m.id, 
            batch_number=med.batch.batch_number,
            expiry_date=med.batch.expiry_date,
            quantity=med.batch.current_stock,
            unit_cost=med.batch.purchase_price,
            selling_price=med.batch.sale_price,
            grn_id=None
        ))
    
    # 3. History Log
    db.add(ProductHistory(product_id=new_m.id, user_id=user.id, change_type="CREATE", changes={"action": "Initial Creation"}))
    
    db.flush()
    new_m_id = new_m.id
    db.commit()
    # db.refresh(new_m) -- REMOVED per multi-tenant best practice
    
    # Restore tenant search path
    tenant_schema = db.info.get('tenant_schema')
    if tenant_schema:
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        
    new_m = db.query(Product).filter(Product.id == new_m_id).first()
    return new_m
