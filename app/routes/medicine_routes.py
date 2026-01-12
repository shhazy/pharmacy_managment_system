from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..models import Product, ProductIngredient, ProductSupplier, ProductHistory, Batch, User
from ..schemas import MedicineCreate
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

@router.get("/search")
def search_products(q: str, db: Session = Depends(get_db_with_tenant)):
    return db.query(Product).filter(Product.product_name.ilike(f"%{q}%")).all()

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
    # 1. Validation
    if med.product_code and db.query(Product).filter(Product.product_code == med.product_code).first():
        raise HTTPException(status_code=400, detail="Product Code already exists")
        
    new_m = Product(
        product_name=med.name or med.product_name if hasattr(med, 'product_name') else med.name,
        generic_name=med.generic_name, brand_name=med.brand_name,
        category_id=med.category_id, manufacturer_id=med.manufacturer_id,
        uom=med.uom, pack_size=med.pack_size, pack_type=med.pack_type,
        moq=med.moq, max_stock=med.max_stock, shelf_life_months=med.shelf_life_months,
        tax_rate=med.tax_rate, discount_allowed=med.discount_allowed, max_discount=med.max_discount,
        is_narcotic=med.is_narcotic, schedule_type=med.schedule_type,
        barcode=med.barcode, hsn_code=med.hsn_code, product_code=med.product_code,
        image_url=med.image_url, description=med.description,
        pregnancy_category=med.pregnancy_category, lactation_safety=med.lactation_safety,
        storage_conditions=med.storage_conditions, license_number=med.license_number,
        is_cold_chain=med.is_cold_chain
    )
    db.add(new_m); db.flush()
    
    # 2. Relations
    for ing in med.ingredients:
        db.add(ProductIngredient(product_id=new_m.id, **ing.dict()))
        
    for sup in med.suppliers:
        db.add(ProductSupplier(product_id=new_m.id, **sup.dict()))
        
    if med.batch:
        store_id = med.batch.store_id or user.store_id
        db.add(Batch(product_id=new_m.id, **med.batch.dict(exclude={'store_id'}), store_id=store_id, initial_stock=med.batch.current_stock))
    
    # 3. History Log
    db.add(ProductHistory(product_id=new_m.id, user_id=user.id, change_type="CREATE", changes={"action": "Initial Creation"}))
    
    db.commit(); db.refresh(new_m)
    return new_m
