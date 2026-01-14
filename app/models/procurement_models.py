from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text
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
    
    quantity = Column(Integer)
    unit_cost = Column(Float)
    discount_percent = Column(Float, default=0.0)
    total_cost = Column(Float)
    
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
    
    grn = relationship("GRN", back_populates="items")
    product = relationship("Product")
