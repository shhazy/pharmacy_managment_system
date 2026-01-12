from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BatchBase(BaseModel):
    batch_number: str
    expiry_date: datetime
    purchase_price: float
    mrp: float
    sale_price: float
    current_stock: int
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
    name: str
    generic_name: str
    brand_name: str
    category_id: int
    manufacturer_id: int
    image_url: Optional[str] = None
    description: Optional[str] = None
    
    # Identification
    barcode: Optional[str] = None
    hsn_code: Optional[str] = None
    product_code: Optional[str] = None
    
    # Packaging
    uom: str
    pack_size: str
    pack_type: Optional[str] = None
    moq: int = 1
    max_stock: int = 1000
    shelf_life_months: int = 24
    
    # Pricing
    tax_rate: float = 0.0
    discount_allowed: bool = True
    max_discount: float = 0.0
    
    # Safety
    is_narcotic: bool = False
    schedule_type: Optional[str] = "G"
    pregnancy_category: Optional[str] = None
    lactation_safety: Optional[str] = None
    storage_conditions: Optional[str] = None
    license_number: Optional[str] = None
    is_cold_chain: bool = False
    
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
    tax_percent: float = 0

class InvoiceCreate(BaseModel):
    patient_id: Optional[int] = None
    items: List[POSItem]
    payment_method: str = "Cash"
    discount_amount: float = 0
