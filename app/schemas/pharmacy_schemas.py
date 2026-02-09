from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

# --- Placeholders/Bases ---

class BatchBase(BaseModel):
    batch_number: str
    expiry_date: Optional[datetime] = None
    stock: int = 0
    unit_cost: float = 0.0

class IngredientBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProductSupplierBase(BaseModel):
    supplier_id: int
    product_id: int
    is_preferred: bool = False

# --- Medicine/Product Schemas ---

class MedicineCreate(BaseModel):
    product_name: str
    category_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    product_group_id: Optional[int] = None
    manufacturer_id: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    min_stock: float = 0.0
    max_stock: float = 100.0
    purchase_conv_factor: int = 1
    base_unit_id: Optional[int] = None
    tax_percent: float = 0.0
    # Add other fields as necessary from Product model

# --- POS/Invoice Schemas ---

class POSItem(BaseModel):
    medicine_id: int
    batch_id: Optional[int] = None
    quantity: float
    unit_price: float
    total_price: Optional[float] = None # Calculated in backend if missing
    discount_amount: float = 0.0
    discount_percent: float = 0.0
    tax_amount: Optional[float] = 0.0
    tax_percent: float = 0.0
    retail_price: Optional[float] = None
    batch_number: Optional[str] = None
    
class InvoiceCreate(BaseModel):
    customer_id: Optional[int] = None
    patient_id: Optional[int] = None
    customer_name: Optional[str] = None
    store_id: Optional[int] = 1
    items: List[POSItem]
    sub_total: Optional[float] = None # Calculated in backend if missing
    net_total: Optional[float] = None # Calculated in backend if missing
    paid_amount: float = 0.0
    discount_amount: float = 0.0
    invoice_discount: float = 0.0
    adjustment: float = 0.0
    tax_amount: float = 0.0
    payment_method: str = "Cash"
    remarks: Optional[str] = None
    status: str = "Paid"
