from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..models import (
    Product, LineItem, Category, SubCategory, ProductGroup, CategoryGroup,
    Generic, CalculateSeason, Manufacturer, Rack, Supplier, PurchaseConversionUnit, User,
    ProductSupplier, ProductIngredient, ProductHistory,
    PurchaseOrderItem, GRNItem, InvoiceItem, StockInventory, StockTransfer, StockAdjustment
)
from sqlalchemy.exc import IntegrityError
from ..auth import get_db_with_tenant, get_current_tenant_user
from ..schemas.common_schemas import PaginatedResponse
from ..utils.pagination import paginate

router = APIRouter()

# ============ SCHEMAS ============

class ProductSupplierData(BaseModel):
    supplier_id: int
    supplier_product_code: Optional[str] = None
    lead_time_days: int = 1
    min_qty: int = 1
    cost_price: float = 0.0

class ProductSupplierResponse(BaseModel):
    id: int
    supplier_id: int
    supplier_product_code: Optional[str] = None
    lead_time_days: int
    min_qty: int
    cost_price: float
    
    class Config:
        from_attributes = True

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
    preferred_purchase_unit_id: Optional[int] = None
    preferred_pos_unit_id: Optional[int] = None
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
    suppliers: List[ProductSupplierData] = []

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
    preferred_purchase_unit_id: Optional[int] = None
    preferred_pos_unit_id: Optional[int] = None
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
    suppliers: Optional[List[ProductSupplierData]] = None

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
    preferred_purchase_unit_id: Optional[int]
    preferred_pos_unit_id: Optional[int]
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
    product_suppliers: List[ProductSupplierResponse] = []
    
    class Config:
        from_attributes = True

# ============ ROUTES ============

@router.get("/", response_model=PaginatedResponse[ProductResponse])
def list_products(
    page: int = 1, 
    page_size: int = 10, 
    search: Optional[str] = None,
    sort_by: str = "id",
    order: str = "desc",
    db: Session = Depends(get_db_with_tenant), 
    user: User = Depends(get_current_tenant_user)
):
    query = db.query(Product)
    
    if search:
        # Simple search by name or ID
        if search.isdigit():
            query = query.filter((Product.product_name.ilike(f"%{search}%")) | (Product.id == int(search)))
        else:
            query = query.filter(Product.product_name.ilike(f"%{search}%"))
    
    # Sorting
    if sort_by and hasattr(Product, sort_by):
        column = getattr(Product, sort_by)
        if order == "asc":
            query = query.order_by(column.asc())
        else:
            query = query.order_by(column.desc())
    else:
        query = query.order_by(Product.id.desc())
    
    items, total, total_pages = paginate(query, page, page_size)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    product_data = product.dict()
    suppliers_data = product_data.pop('suppliers', [])
    
    # Manual uniqueness check (trimmed and case-insensitive)
    name_clean = product_data['product_name'].strip()
    existing = db.query(Product).filter(func.lower(func.trim(Product.product_name)) == name_clean.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with name '{name_clean}' already exists.")
    
    product_data['product_name'] = name_clean
    
    try:
        db_product = Product(**product_data)
        db.add(db_product)
        db.flush()
        db_product_id = db_product.id
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="A product with this name already exists.")

    # Add Suppliers
    for sup in suppliers_data:
        db_sup = ProductSupplier(product_id=db_product_id, **sup)
        db.add(db_sup)
    db.commit()
    
    # db.refresh(db_product)
    
    # Restore tenant search path
    tenant_schema = db.info.get('tenant_schema')
    if tenant_schema:
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))

    db_product = db.query(Product).filter(Product.id == db_product_id).first()
    return db_product

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product: ProductUpdate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product.dict(exclude_unset=True)
    suppliers_data = update_data.pop('suppliers', None)

    # Manual uniqueness check if name is being changed
    if 'product_name' in update_data:
        name_clean = update_data['product_name'].strip()
        existing = db.query(Product).filter(
            func.lower(func.trim(Product.product_name)) == name_clean.lower(),
            Product.id != product_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Product with name '{name_clean}' already exists.")
        update_data['product_name'] = name_clean

    for field, value in update_data.items():
        setattr(db_product, field, value)
    
    if suppliers_data is not None:
        # Clear existing
        db.query(ProductSupplier).filter(ProductSupplier.product_id == product_id).delete()
        # Add new
        for sup in suppliers_data:
            db_sup = ProductSupplier(product_id=product_id, **sup)
            db.add(db_sup)
    
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="A product with this name already exists.")
    # db.refresh(db_product)

    # Restore tenant search path
    tenant_schema = db.info.get('tenant_schema')
    if tenant_schema:
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))

    db_product = db.query(Product).filter(Product.id == product_id).first()
    return db_product

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # 1. Check for historical transactions (Dependencies)
    has_po = db.query(PurchaseOrderItem).filter(PurchaseOrderItem.product_id == product_id).first() is not None
    has_grn = db.query(GRNItem).filter(GRNItem.product_id == product_id).first() is not None
    has_sales = db.query(InvoiceItem).filter(InvoiceItem.medicine_id == product_id).first() is not None
    has_stock = db.query(StockInventory).filter(StockInventory.product_id == product_id).first() is not None
    has_transfers = db.query(StockTransfer).filter(StockTransfer.product_id == product_id).first() is not None
    has_adjustments = db.query(StockAdjustment).filter(StockAdjustment.product_id == product_id).first() is not None

    if any([has_po, has_grn, has_sales, has_stock, has_transfers, has_adjustments]):
        # Fallback to Soft Delete if transactions exist
        db_product.active = False
        db.commit()
        return {
            "message": "Product has historical transactions and cannot be hard deleted. It has been deactivated instead.",
            "type": "soft_delete"
        }
    
    # 2. Hard Delete (No transactions found)
    try:
        # Delete dependent metadata first
        db.query(ProductSupplier).filter(ProductSupplier.product_id == product_id).delete()
        db.query(ProductIngredient).filter(ProductIngredient.product_id == product_id).delete()
        db.query(ProductHistory).filter(ProductHistory.product_id == product_id).delete()
        
        # Delete the product itself
        db.delete(db_product)
        db.commit()
        return {
            "message": "Product and all associated metadata successfully hard deleted.",
            "type": "hard_delete"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error during hard deletion: {str(e)}")
