from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

# --- PROCUREMENT & TRANSFERS ---

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True, index=True)
    po_no = Column(String, unique=True, index=True, nullable=True) # Generated final PO number
    reference_no = Column(String, index=True, nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    
    issue_date = Column(DateTime, default=datetime.utcnow)
    delivery_date = Column(DateTime, nullable=True)
    
    sub_total = Column(Float, default=0.0)
    total_tax = Column(Float, default=0.0)
    total_discount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    
    status = Column(String, default="Pending") # Pending, Received, Cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    quantity = Column(Integer) # Total units
    unit_cost = Column(Float)
    discount_percent = Column(Float, default=0.0)
    total_cost = Column(Float)
    
    purchase_conversion_unit_id = Column(Integer, ForeignKey("purchase_conversion_units.id"), nullable=True)
    factor = Column(Integer, default=1)
    
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")

class StockTransfer(Base):
    __tablename__ = "stock_transfers"
    id = Column(Integer, primary_key=True, index=True)
    from_store_id = Column(Integer, ForeignKey("stores.id"))
    to_store_id = Column(Integer, ForeignKey("stores.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    status = Column(String, default="Sent")
    created_at = Column(DateTime, default=datetime.utcnow)

class GRN(Base):
    __tablename__ = "grns"
    id = Column(Integer, primary_key=True, index=True)
    custom_grn_no = Column(String, unique=True, index=True) # e.g., GRN-YYMMDD...
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    
    invoice_no = Column(String, nullable=True)
    invoice_date = Column(DateTime, nullable=True)
    bill_no = Column(String, nullable=True)
    bill_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    payment_mode = Column(String, default="Cash")
    comments = Column(Text, nullable=True)
    
    # Financials
    sub_total = Column(Float, default=0.0)
    loading_exp = Column(Float, default=0.0)
    freight_exp = Column(Float, default=0.0)
    other_exp = Column(Float, default=0.0)
    purchase_tax = Column(Float, default=0.0)
    advance_tax = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    net_total = Column(Float, default=0.0)
    
    status = Column(String, default="Completed")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    items = relationship("GRNItem", back_populates="grn")
    supplier = relationship("Supplier")
    purchase_order = relationship("PurchaseOrder")

class GRNItem(Base):
    __tablename__ = "grn_items"
    id = Column(Integer, primary_key=True, index=True)
    grn_id = Column(Integer, ForeignKey("grns.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    batch_no = Column(String)
    expiry_date = Column(DateTime)
    
    pack_size = Column(Integer, default=1)
    quantity = Column(Integer) # Units
    
    unit_cost = Column(Float)
    total_cost = Column(Float)
    retail_price = Column(Float)
    foc_quantity = Column(Integer, default=0)
    
    purchase_conversion_unit_id = Column(Integer, ForeignKey("purchase_conversion_units.id"), nullable=True)
    factor = Column(Integer, default=1)
    
    grn = relationship("GRN", back_populates="items")
    product = relationship("Product")

# --- STOCK INVENTORY MANAGEMENT ---

class StockInventory(Base):
    """
    Detailed inventory tracking per batch with GRN traceability.
    This table maintains granular stock records linked to specific GRN entries.
    """
    __tablename__ = "stock_inventory"
    
    inventory_id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number = Column(String(100), index=True)
    expiry_date = Column(DateTime, nullable=True)
    
    quantity = Column(Float, nullable=False, default=0)
    unit_cost = Column(Float, nullable=True)  # Landed cost per unit
    selling_price = Column(Float, nullable=True)
    retail_price = Column(Float, nullable=True) # MRP per batch
    tax_percent = Column(Float, default=0.0) # GST % per batch
    
    warehouse_location = Column(String(100), nullable=True)  # Shelf/rack location
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    grn_id = Column(Integer, ForeignKey("grns.id"), nullable=True)  # Trace back to GRN if available
    
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    supplier = relationship("Supplier")
    grn = relationship("GRN")
    adjustments = relationship("StockAdjustment", back_populates="inventory")

class StockAdjustment(Base):
    """
    Track all stock adjustments with full audit trail.
    Handles physical counts, damages, expiry, theft, returns, etc.
    """
    __tablename__ = "stock_adjustments"
    
    adjustment_id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number = Column(String(100), nullable=True)
    inventory_id = Column(Integer, ForeignKey("stock_inventory.inventory_id"), nullable=True)
    
    adjustment_type = Column(String(50), nullable=False)  
    # Types: 'physical_count', 'damage', 'expiry', 'theft', 'return_to_supplier', 'other'
    
    quantity_adjusted = Column(Float, nullable=False)  # Negative for reductions
    previous_quantity = Column(Float, nullable=True)
    new_quantity = Column(Float, nullable=True)
    
    reason = Column(Text, nullable=True)
    reference_number = Column(String(100), nullable=True)  # Physical count sheet #, damage report #, etc.
    
    adjustment_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    adjusted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    status = Column(String(20), default="pending")  # 'pending', 'approved', 'rejected'
    
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product")
    inventory = relationship("StockInventory", back_populates="adjustments")
    adjuster = relationship("User", foreign_keys=[adjusted_by])
    approver = relationship("User", foreign_keys=[approved_by])

