from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Stock Inventory Schemas ---

class StockInventoryBase(BaseModel):
    product_id: int
    batch_number: Optional[str] = None
    expiry_date: Optional[datetime] = None
    quantity: float
    unit_cost: Optional[float] = None
    selling_price: Optional[float] = None
    warehouse_location: Optional[str] = None
    supplier_id: Optional[int] = None
    grn_id: Optional[int] = None
    is_available: bool = True

class StockInventoryCreate(StockInventoryBase):
    pass

class StockInventoryUpdate(BaseModel):
    quantity: Optional[float] = None
    unit_cost: Optional[float] = None
    selling_price: Optional[float] = None
    warehouse_location: Optional[str] = None
    is_available: Optional[bool] = None

class StockInventoryResponse(StockInventoryBase):
    inventory_id: int
    created_at: datetime
    last_updated: datetime
    
    class Config:
        from_attributes = True

# --- Stock Adjustment Schemas ---

class StockAdjustmentBase(BaseModel):
    product_id: int
    batch_number: Optional[str] = None
    inventory_id: Optional[int] = None
    adjustment_type: str  # 'physical_count', 'damage', 'expiry', 'theft', 'return_to_supplier', 'other'
    quantity_adjusted: float
    previous_quantity: Optional[float] = None
    new_quantity: Optional[float] = None
    reason: Optional[str] = None
    reference_number: Optional[str] = None
    adjustment_date: datetime
    adjusted_by: Optional[int] = None
    approved_by: Optional[int] = None
    status: str = "pending"  # 'pending', 'approved', 'rejected'

class StockAdjustmentCreate(StockAdjustmentBase):
    pass

class StockAdjustmentUpdate(BaseModel):
    status: Optional[str] = None
    approved_by: Optional[int] = None
    reason: Optional[str] = None

class StockAdjustmentResponse(StockAdjustmentBase):
    adjustment_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
