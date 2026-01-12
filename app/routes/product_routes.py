from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..models import (
    Product, LineItem, Category, SubCategory, ProductGroup, CategoryGroup,
    Generic, CalculateSeason, Manufacturer, Rack, Supplier, PurchaseConversionUnit, User
)
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

# ============ SCHEMAS ============

class ProductCreate(BaseModel):
    line_item_id: Optional[int] = None
    product_name: str
    category_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    product_group_id: Optional[int] = None
    category_group_id: Optional[int] = None
    generics_id: Optional[int] = None
    cal_season_id: Optional[int] = None
    manufacturer_id: Optional[int] = None
    rack_id: Optional[int] = None
    supplier_id: Optional[int] = None
    purchase_conv_unit_id: Optional[int] = None
    control_drug: bool = False
    purchase_conv_factor: Optional[int] = None
    average_cost: Optional[float] = None
    date: Optional[datetime] = None
    retail_price: Optional[float] = None
    active: bool = True
    technical_details: Optional[str] = None
    internal_comments: Optional[str] = None
    product_type: int = 1  # 1 = Basic, 2 = Assembly
    min_inventory_level: Optional[int] = None
    optimal_inventory_level: Optional[int] = None
    max_inventory_level: Optional[int] = None
    allow_below_cost_sale: bool = False
    allow_price_change: bool = True

class ProductUpdate(BaseModel):
    line_item_id: Optional[int] = None
    product_name: Optional[str] = None
    category_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    product_group_id: Optional[int] = None
    category_group_id: Optional[int] = None
    generics_id: Optional[int] = None
    cal_season_id: Optional[int] = None
    manufacturer_id: Optional[int] = None
    rack_id: Optional[int] = None
    supplier_id: Optional[int] = None
    purchase_conv_unit_id: Optional[int] = None
    control_drug: Optional[bool] = None
    purchase_conv_factor: Optional[int] = None
    average_cost: Optional[float] = None
    date: Optional[datetime] = None
    retail_price: Optional[float] = None
    active: Optional[bool] = None
    technical_details: Optional[str] = None
    internal_comments: Optional[str] = None
    product_type: Optional[int] = None
    min_inventory_level: Optional[int] = None
    optimal_inventory_level: Optional[int] = None
    max_inventory_level: Optional[int] = None
    allow_below_cost_sale: Optional[bool] = None
    allow_price_change: Optional[bool] = None

class ProductResponse(BaseModel):
    id: int
    line_item_id: Optional[int]
    product_name: str
    category_id: Optional[int]
    sub_category_id: Optional[int]
    product_group_id: Optional[int]
    category_group_id: Optional[int]
    generics_id: Optional[int]
    cal_season_id: Optional[int]
    manufacturer_id: Optional[int]
    rack_id: Optional[int]
    supplier_id: Optional[int]
    purchase_conv_unit_id: Optional[int]
    control_drug: bool
    purchase_conv_factor: Optional[int]
    average_cost: Optional[float]
    date: Optional[datetime]
    retail_price: Optional[float]
    active: bool
    technical_details: Optional[str]
    internal_comments: Optional[str]
    product_type: int
    min_inventory_level: Optional[int]
    optimal_inventory_level: Optional[int]
    max_inventory_level: Optional[int]
    allow_below_cost_sale: bool
    allow_price_change: bool
    
    class Config:
        from_attributes = True

# ============ ROUTES ============

@router.get("/", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    return db.query(Product).all()

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product: ProductUpdate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_product.active = False
    db.commit()
    return {"message": "Product deleted successfully"}
