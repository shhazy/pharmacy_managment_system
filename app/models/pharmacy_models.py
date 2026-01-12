from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

# --- PHARMACY CORE ---

class Manufacturer(Base):
    __tablename__ = "manufacturers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    contact_info = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Antibiotics, Painkillers...
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    
    # Core fields
    line_item_id = Column(Integer, ForeignKey("line_items.id"), nullable=True)
    product_name = Column(String, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    sub_category_id = Column(Integer, ForeignKey("sub_categories.id"), nullable=True)
    product_group_id = Column(Integer, ForeignKey("product_groups.id"), nullable=True)
    category_group_id = Column(Integer, ForeignKey("category_groups.id"), nullable=True)
    generics_id = Column(Integer, ForeignKey("generics.id"), nullable=True)
    cal_season_id = Column(Integer, ForeignKey("calculate_seasons.id"), nullable=True)
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id"), nullable=True)
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    purchase_conv_unit_id = Column(Integer, ForeignKey("purchase_conversion_units.id"), nullable=True)
    
    # Control and flags
    control_drug = Column(Boolean, default=False)  # 1 or 0
    active = Column(Boolean, default=True)  # 1 or 0
    product_type = Column(Integer, default=1)  # 1 = Basic, 2 = Assembly
    allow_below_cost_sale = Column(Boolean, default=False)  # 1 or 0
    allow_price_change = Column(Boolean, default=True)  # 1 or 0
    
    # Numeric fields
    purchase_conv_factor = Column(Integer, nullable=True)
    average_cost = Column(Float, nullable=True)
    retail_price = Column(Float, nullable=True)
    min_inventory_level = Column(Integer, nullable=True)
    optimal_inventory_level = Column(Integer, nullable=True)
    max_inventory_level = Column(Integer, nullable=True)
    
    # Date and text fields
    date = Column(DateTime, nullable=True)
    technical_details = Column(Text, nullable=True)
    internal_comments = Column(Text, nullable=True)
    
    # Legacy fields (keeping for backward compatibility)
    generic_name = Column(String, nullable=True)
    brand_name = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    strength = Column(String, nullable=True)
    reorder_level = Column(Integer, default=50)
    is_narcotic = Column(Boolean, default=False)
    schedule_type = Column(String, nullable=True)
    composition = Column(Text, nullable=True)
    side_effects = Column(Text, nullable=True)
    interactions = Column(JSON, nullable=True)
    contraindications = Column(Text, nullable=True)
    dosage_info = Column(Text, nullable=True)
    barcode = Column(String, index=True, nullable=True)
    hsn_code = Column(String, nullable=True)
    product_code = Column(String, unique=True, index=True, nullable=True)
    ndc = Column(String, nullable=True)
    uom = Column(String, nullable=True)
    pack_size = Column(String, nullable=True)
    pack_type = Column(String, nullable=True)
    moq = Column(Integer, default=1)
    max_stock = Column(Integer, default=1000)
    shelf_life_months = Column(Integer, default=24)
    gross_weight = Column(String, nullable=True)
    dimensions = Column(String, nullable=True)
    tax_rate = Column(Float, default=0.0)
    discount_allowed = Column(Boolean, default=True)
    max_discount = Column(Float, default=0.0)
    pregnancy_category = Column(String, nullable=True)
    lactation_safety = Column(String, nullable=True)
    storage_conditions = Column(String, nullable=True)
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
    address = Column(String, nullable=True)
    gst_number = Column(String, nullable=True)
    ledger_balance = Column(Float, default=0.0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
