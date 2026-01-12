from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, DateTime, Float, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

# --- PUBLIC SCHEMA MODELS ---

class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    subdomain = Column(String, unique=True, index=True)
    schema_name = Column(String, unique=True)
    admin_username = Column(String)
    admin_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SuperAdmin(Base):
    __tablename__ = "superadmins"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- TENANT SPECIFIC MODELS ---

# Junction tables
user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True)
)

role_permissions = Table(
    "role_permissions", Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True)
)

class Store(Base):
    """Multiple Branch Support"""
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    is_warehouse = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    permissions = relationship("Permission", secondary=role_permissions, backref="roles")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    roles = relationship("Role", secondary=user_roles, backref="users")

# --- PHARMACY CORE ---

class Manufacturer(Base):
    __tablename__ = "manufacturers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    contact_info = Column(Text)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True) # Antibiotics, Painkillers...

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    generic_name = Column(String, index=True)
    brand_name = Column(String, index=True)
    image_url = Column(String, nullable=True)
    
    category_id = Column(Integer, ForeignKey("categories.id"))
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id"))
    
    unit = Column(String) # Tablet, Syrup
    strength = Column(String) # 500mg
    reorder_level = Column(Integer, default=50)
    
    is_narcotic = Column(Boolean, default=False)
    schedule_type = Column(String) # H, H1, X
    
    # Clinical Data
    composition = Column(Text)
    side_effects = Column(Text)
    interactions = Column(JSON) # [{'other_med_id': 1, 'effect': 'severe'}]
    contraindications = Column(Text)
    dosage_info = Column(Text)
    
    # Identification & Classification
    barcode = Column(String, index=True, nullable=True)
    hsn_code = Column(String, nullable=True)
    product_code = Column(String, unique=True, index=True, nullable=True)
    ndc = Column(String, nullable=True)
    
    # Packaging & Dimensions
    uom = Column(String) # Strip, Bottle
    pack_size = Column(String) # 10s, 100ml
    pack_type = Column(String) # Blister, Vial
    moq = Column(Integer, default=1)
    max_stock = Column(Integer, default=1000)
    shelf_life_months = Column(Integer, default=24)
    gross_weight = Column(String, nullable=True) # e.g. "50g"
    dimensions = Column(String, nullable=True) # "10x5x2 cm"
    
    # Pricing & Tax
    tax_rate = Column(Float, default=0.0)
    discount_allowed = Column(Boolean, default=True)
    max_discount = Column(Float, default=0.0)
    
    # Safety & Regulatory
    pregnancy_category = Column(String, nullable=True) # A, B, C...
    lactation_safety = Column(String, nullable=True)
    storage_conditions = Column(String, nullable=True) # Room Temp, 2-8C
    license_number = Column(String, nullable=True)
    is_cold_chain = Column(Boolean, default=False)
    is_temp_log_required = Column(Boolean, default=False)
    
    description = Column(Text, nullable=True)
    
    batches = relationship("Batch", back_populates="product")
    ingredients = relationship("ProductIngredient", back_populates="product")
    product_suppliers = relationship("ProductSupplier", back_populates="product")
    history = relationship("ProductHistory", back_populates="product")

class ProductIngredient(Base):
    __tablename__ = "product_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String, index=True)
    strength = Column(String) # 500
    unit = Column(String) # mg
    percentage = Column(String, nullable=True) # 10%
    product = relationship("Product", back_populates="ingredients")

class ProductSupplier(Base):
    __tablename__ = "product_suppliers"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    supplier_product_code = Column(String, nullable=True)
    lead_time_days = Column(Integer, default=1)
    min_qty = Column(Integer, default=1)
    cost_price = Column(Float, default=0.0)
    product = relationship("Product", back_populates="product_suppliers")

class ProductHistory(Base):
    __tablename__ = "product_history"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    user_id = Column(Integer, nullable=True) # ID of user who made change
    change_type = Column(String) # CREATE, UPDATE
    changes = Column(JSON) # Diff of changes
    created_at = Column(DateTime, default=datetime.utcnow)
    product = relationship("Product", back_populates="history")

class Batch(Base):
    __tablename__ = "batches"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    store_id = Column(Integer, ForeignKey("stores.id"))
    batch_number = Column(String, index=True)
    expiry_date = Column(DateTime)
    purchase_price = Column(Float)
    mrp = Column(Float)
    sale_price = Column(Float)
    current_stock = Column(Integer)
    initial_stock = Column(Integer)
    product = relationship("Product", back_populates="batches")

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    gst_number = Column(String)
    ledger_balance = Column(Float, default=0.0)

# --- PROCUREMENT & TRANSFERS ---

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    total_amount = Column(Float)
    status = Column(String, default="Pending") # Pending, Received, Cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

class StockTransfer(Base):
    __tablename__ = "stock_transfers"
    id = Column(Integer, primary_key=True, index=True)
    from_store_id = Column(Integer, ForeignKey("stores.id"))
    to_store_id = Column(Integer, ForeignKey("stores.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    status = Column(String, default="Sent")
    created_at = Column(DateTime, default=datetime.utcnow)

# --- SALES & BILLING ---

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String, index=True)
    medical_history = Column(Text)
    credit_limit = Column(Float, default=0.0)
    outstanding_balance = Column(Float, default=0.0)

class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_name = Column(String)
    image_path = Column(String) # Scanned doc
    created_at = Column(DateTime, default=datetime.utcnow)

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    store_id = Column(Integer, ForeignKey("stores.id"))
    
    sub_total = Column(Float)
    tax_amount = Column(Float)
    discount_amount = Column(Float)
    net_total = Column(Float)
    paid_amount = Column(Float)
    
    payment_method = Column(String)
    status = Column(String, default="Paid") # Paid, Partial, Credit
    
    created_at = Column(DateTime, default=datetime.utcnow)
    items = relationship("InvoiceItem", back_populates="invoice")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    batch_id = Column(Integer, ForeignKey("batches.id"))
    quantity = Column(Integer)
    unit_price = Column(Float)
    total_price = Column(Float)
    invoice = relationship("Invoice", back_populates="items")

class SalesReturn(Base):
    __tablename__ = "sales_returns"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    refund_amount = Column(Float)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- SERVICES & LOGS ---

class TemperatureLog(Base):
    __tablename__ = "temperature_logs"
    id = Column(Integer, primary_key=True, index=True)
    fridge_id = Column(String)
    temperature = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class RegulatoryLog(Base):
    __tablename__ = "regulatory_logs"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    action = Column(String) # Dispensed, Received
    quantity = Column(Integer)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"))
    change_qty = Column(Integer) # Negative for damage/waste, Positive for corrections
    reason = Column(String) # Waste, Expiry, Damage, Correction
    created_at = Column(DateTime, default=datetime.utcnow)
