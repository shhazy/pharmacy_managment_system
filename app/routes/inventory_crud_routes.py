from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..models import (
    LineItem, Category, SubCategory, ProductGroup, CategoryGroup,
    Generic, CalculateSeason, Manufacturer, Rack, Supplier, PurchaseConversionUnit, User
)
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

# ============ SCHEMAS ============

class BaseInventoryItem(BaseModel):
    name: str

class InventoryItemCreate(BaseInventoryItem):
    pass

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class InventoryItemResponse(BaseInventoryItem):
    id: int
    created_by: Optional[int]
    updated_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class SubCategoryCreate(BaseModel):
    name: str
    category_id: int

class SubCategoryUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None

class SubCategoryResponse(BaseModel):
    id: int
    name: str
    category_id: int
    created_by: Optional[int]
    updated_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

# ============ GENERIC CRUD FUNCTIONS ============

def create_crud_routes(model_class, router_prefix: str, create_schema, update_schema, response_schema):
    """Generic function to create CRUD routes for a model"""
    
    @router.get(f"/{router_prefix}", response_model=List[response_schema])
    def list_items(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
        return db.query(model_class).filter(model_class.is_active == True).all()
    
    @router.get(f"/{router_prefix}/all", response_model=List[response_schema])
    def list_all_items(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
        return db.query(model_class).all()
    
    @router.post(f"/{router_prefix}", response_model=response_schema)
    def create_item(item: create_schema, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
        try:
            db_item = model_class(**item.dict(), created_by=user.id, updated_by=user.id)
            db.add(db_item)
            db.flush()
            item_id = db_item.id
            db.commit()
            
            # Restore tenant search path after commit
            tenant_schema = db.info.get('tenant_schema')
            if tenant_schema:
                db.execute(text(f"SET search_path TO {tenant_schema}, public"))
            
            db_item = db.query(model_class).filter(model_class.id == item_id).first()
            return db_item
        except Exception as e:
            db.rollback()
            print(f"DEBUG ERROR in create_item ({router_prefix}): {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.get(f"/{router_prefix}/{{item_id}}", response_model=response_schema)
    def get_item(item_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
        item = db.query(model_class).filter(model_class.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"{model_class.__name__} not found")
        return item
    
    @router.put(f"/{router_prefix}/{{item_id}}", response_model=response_schema)
    def update_item(item_id: int, item: update_schema, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
        db_item = db.query(model_class).filter(model_class.id == item_id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail=f"{model_class.__name__} not found")
        
        update_data = item.dict(exclude_unset=True)
        update_data['updated_by'] = user.id
        update_data['updated_at'] = datetime.utcnow()
        
        for field, value in update_data.items():
            setattr(db_item, field, value)
        
        db.commit()
        # Restore tenant search path
        tenant_schema = db.info.get('tenant_schema')
        if tenant_schema:
            db.execute(text(f"SET search_path TO {tenant_schema}, public"))
            
        db_item = db.query(model_class).filter(model_class.id == item_id).first()
        return db_item
    
    @router.delete(f"/{router_prefix}/{{item_id}}")
    def delete_item(item_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
        db_item = db.query(model_class).filter(model_class.id == item_id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail=f"{model_class.__name__} not found")
        
        # Soft delete
        db_item.is_active = False
        db_item.updated_by = user.id
        db_item.updated_at = datetime.utcnow()
        db.commit()
        return {"message": f"{model_class.__name__} deleted successfully"}

# ============ LINE ITEMS ============
create_crud_routes(LineItem, "line-items", InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse)

# ============ CATEGORIES ============
create_crud_routes(Category, "categories", InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse)

# ============ PRODUCT GROUPS ============
create_crud_routes(ProductGroup, "product-groups", InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse)

# ============ CATEGORY GROUPS ============
create_crud_routes(CategoryGroup, "category-groups", InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse)

# ============ GENERICS ============
create_crud_routes(Generic, "generics", InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse)

# ============ CALCULATE SEASONS ============
create_crud_routes(CalculateSeason, "calculate-seasons", InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse)

# ============ MANUFACTURERS ============
create_crud_routes(Manufacturer, "manufacturers", InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse)

# ============ RACKS ============
create_crud_routes(Rack, "racks", InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse)

# ============ SUPPLIERS ============
create_crud_routes(Supplier, "suppliers", InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse)

# ============ PURCHASE CONVERSION UNITS ============
create_crud_routes(PurchaseConversionUnit, "purchase-conversion-units", InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse)

# ============ SUB CATEGORIES (Special handling due to foreign key) ============

@router.get("/sub-categories", response_model=List[SubCategoryResponse])
def list_sub_categories(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    return db.query(SubCategory).filter(SubCategory.is_active == True).all()

@router.get("/sub-categories/all", response_model=List[SubCategoryResponse])
def list_all_sub_categories(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    return db.query(SubCategory).all()

@router.post("/sub-categories", response_model=SubCategoryResponse)
def create_sub_category(item: SubCategoryCreate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    try:
        # Verify category exists
        category = db.query(Category).filter(Category.id == item.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        db_item = SubCategory(**item.dict(), created_by=user.id, updated_by=user.id)
        db.add(db_item)
        db.flush()
        item_id = db_item.id
        db.commit()
        
        # Restore tenant search path
        tenant_schema = db.info.get('tenant_schema')
        if tenant_schema:
            db.execute(text(f"SET search_path TO {tenant_schema}, public"))
            
        db_item = db.query(SubCategory).filter(SubCategory.id == item_id).first()
        return db_item
    except Exception as e:
        db.rollback()
        print(f"DEBUG ERROR in create_sub_category: {e}")
        import traceback
        traceback.print_exc()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sub-categories/{item_id}", response_model=SubCategoryResponse)
def get_sub_category(item_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    item = db.query(SubCategory).filter(SubCategory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="SubCategory not found")
    return item

@router.put("/sub-categories/{item_id}", response_model=SubCategoryResponse)
def update_sub_category(item_id: int, item: SubCategoryUpdate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_item = db.query(SubCategory).filter(SubCategory.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="SubCategory not found")
    
    # Verify category exists if updating category_id
    if item.category_id is not None:
        category = db.query(Category).filter(Category.id == item.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = item.dict(exclude_unset=True)
    update_data['updated_by'] = user.id
    update_data['updated_at'] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(db_item, field, value)
    
    db.commit()
    
    # Restore tenant search path
    tenant_schema = db.info.get('tenant_schema')
    if tenant_schema:
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        
    db_item = db.query(SubCategory).filter(SubCategory.id == item_id).first()
    return db_item

@router.delete("/sub-categories/{item_id}")
def delete_sub_category(item_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_item = db.query(SubCategory).filter(SubCategory.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="SubCategory not found")
    
    # Soft delete
    db_item.is_active = False
    db_item.updated_by = user.id
    db_item.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "SubCategory deleted successfully"}
