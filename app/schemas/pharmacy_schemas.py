from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BatchBase(BaseModel):
    batch_number: str
    expiry_date: datetime
    purchase_price: float # maps to unit_cost
    sale_price: float # maps to selling_price
    current_stock: float # maps to quantity
    store_id: Optional[int] = None

class IngredientBase(BaseModel):
    name: str
    strength: str
    unit: str
    percentage: Optional[str] = None

class ProductSupplierBase(BaseModel):
    supplier_id: int
    supplier_product_code: Optional[str] = None
    lead_time_days: int = 1
    min_qty: int = 1
    cost_price: float = 0.0

class MedicineCreate(BaseModel):
    # Core
    # Core
    name: str
    category_id: int
    manufacturer_id: int
    generics_id: Optional[int] = None
    
    # Relationships
    line_item_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    product_group_id: Optional[int] = None
    category_group_id: Optional[int] = None
    rack_id: Optional[int] = None
    supplier_id: Optional[int] = None
    purchase_conv_unit_id: Optional[int] = None
    
    # Relations
    batch: Optional[BatchBase] = None
    ingredients: List[IngredientBase] = []
    suppliers: List[ProductSupplierBase] = []

class POSItem(BaseModel):
    medicine_id: int
    batch_id: int
    quantity: int
    unit_price: float
    discount_percent: float = 0
    discount_amount: float = 0
    tax_percent: float = 0

class InvoiceCreate(BaseModel):
    patient_id: Optional[int] = None
    items: List[POSItem]
    payment_method: str = "Cash"
    discount_amount: float = 0
    status: str = "Paid"
