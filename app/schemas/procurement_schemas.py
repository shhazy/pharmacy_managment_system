from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PurchaseOrderItemBase(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float
    discount_percent: float = 0.0
    total_cost: float
    purchase_conversion_unit_id: Optional[int] = None
    factor: int = 1

class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass

class ProductSimplified(BaseModel):
    id: int
    product_name: str
    retail_price: Optional[float] = 0.0
    purchase_conv_unit_id: Optional[int] = None
    purchase_conv_factor: Optional[int] = 1
    uom: Optional[str] = None
    purchase_conv_unit_name: Optional[str] = None

class PurchaseOrderItemResponse(PurchaseOrderItemBase):
    id: int
    product: Optional[ProductSimplified] = None
    class Config:
        from_attributes = True

class PurchaseOrderBase(BaseModel):
    supplier_id: int
    reference_no: Optional[str] = None
    issue_date: datetime
    delivery_date: Optional[datetime] = None
    sub_total: float = 0.0
    total_tax: float = 0.0
    total_discount: float = 0.0
    total_amount: float = 0.0
    notes: Optional[str] = None
    status: str = "Pending"

class PurchaseOrderCreate(PurchaseOrderBase):
    items: List[PurchaseOrderItemCreate]

class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[int] = None
    reference_no: Optional[str] = None
    issue_date: Optional[datetime] = None
    delivery_date: Optional[datetime] = None
    sub_total: Optional[float] = None
    total_tax: Optional[float] = None
    total_discount: Optional[float] = None
    total_amount: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    items: Optional[List[PurchaseOrderItemCreate]] = None

class PurchaseOrderResponse(PurchaseOrderBase):
    id: int
    po_no: Optional[str] = None
    created_at: datetime
    items: List[PurchaseOrderItemResponse]
    
    class Config:
        from_attributes = True

class POGenerateRequest(BaseModel):
    supplier_ids: List[int]
    method: str  # min, optimal, max, sale, none
    sale_start_date: Optional[datetime] = None
    sale_end_date: Optional[datetime] = None

class POSuggestionItem(BaseModel):
    product_id: int
    product_name: str
    product_code: str
    current_stock: int
    suggested_qty: int
    cost_price: float
    manufacturer: str
    purchase_conv_unit_id: Optional[int] = None
    supplier_id: Optional[int] = None

# --- GRN Schemas ---
class GRNItemCreate(BaseModel):
    product_id: int
    batch_no: str
    expiry_date: datetime
    pack_size: int = 1
    quantity: int
    unit_cost: float
    total_cost: float
    retail_price: float
    foc_quantity: int = 0
    purchase_conversion_unit_id: Optional[int] = None
    factor: int = 1

class GRNCreate(BaseModel):
    supplier_id: int
    po_id: Optional[int] = None
    invoice_no: Optional[str] = None
    invoice_date: Optional[datetime] = None
    bill_no: Optional[str] = None
    bill_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    payment_mode: str = "Cash"
    comments: Optional[str] = None
    
    # Financials
    loading_exp: float = 0
    freight_exp: float = 0
    other_exp: float = 0
    purchase_tax: float = 0
    advance_tax: float = 0
    discount: float = 0
    
    items: List[GRNItemCreate]

class GRNResponse(GRNCreate):
    id: int
    custom_grn_no: str
    sub_total: float
    net_total: float
    created_at: datetime

    class Config:
        orm_mode = True

# --- Stock Adjustment Schemas ---
class StockAdjustmentCreate(BaseModel):
    product_id: int
    inventory_id: Optional[int] = None
    batch_number: Optional[str] = None
    adjustment_type: str  # physical_count, damage, expiry, theft, etc.
    quantity_adjusted: float
    reason: Optional[str] = None
    reference_number: Optional[str] = None

class StockAdjustmentResponse(BaseModel):
    adjustment_id: int
    product_id: int
    batch_number: Optional[str] = None
    inventory_id: Optional[int] = None
    adjustment_type: str
    quantity_adjusted: float
    previous_quantity: Optional[float] = None
    new_quantity: Optional[float] = None
    reason: Optional[str] = None
    reference_number: Optional[str] = None
    adjustment_date: datetime
    status: str
    
    class Config:
        from_attributes = True
