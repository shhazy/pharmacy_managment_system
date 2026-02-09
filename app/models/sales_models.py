from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

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
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    store_id = Column(Integer, ForeignKey("stores.id"))
    customer_name = Column(String, nullable=True) # For walk-in customers
    
    sub_total = Column(Float)
    tax_amount = Column(Float)
    discount_amount = Column(Float)
    invoice_discount = Column(Float, default=0.0)
    net_total = Column(Float)
    paid_amount = Column(Float)
    
    payment_method = Column(String)
    status = Column(String, default="Paid") # Paid, Partial, Credit
    remarks = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    items = relationship("InvoiceItem", back_populates="invoice")
    customer = relationship("Customer")
    user = relationship("User")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    medicine_id = Column(Integer, ForeignKey("products.id"))  # kept column name for compatibility
    batch_id = Column(Integer, ForeignKey("stock_inventory.inventory_id"))
    quantity = Column(Integer)
    unit_price = Column(Float)
    retail_price = Column(Float, nullable=True) # MRP
    tax_amount = Column(Float, default=0.0)
    discount_percent = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total_price = Column(Float)
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")

class SalesReturn(Base):
    __tablename__ = "sales_returns"
    id = Column(Integer, primary_key=True, index=True)
    return_number = Column(String, unique=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True) # Optional for ad-hoc returns
    
    sub_total = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    net_total = Column(Float, default=0.0) # Total amount refunded
    
    reason = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    return_date = Column(DateTime, default=datetime.utcnow)
    
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    items = relationship("SaleReturnItem", back_populates="sales_return")
    invoice = relationship("Invoice")

class SaleReturnItem(Base):
    __tablename__ = "sale_return_items"
    id = Column(Integer, primary_key=True, index=True)
    sales_return_id = Column(Integer, ForeignKey("sales_returns.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    batch_id = Column(Integer, ForeignKey("stock_inventory.inventory_id"))
    
    quantity = Column(Integer)
    unit_price = Column(Float)
    retail_price = Column(Float, nullable=True) # MRP
    tax_amount = Column(Float, default=0.0)
    total_price = Column(Float)
    
    # Relationships
    sales_return = relationship("SalesReturn", back_populates="items")
    product = relationship("Product")
    inventory = relationship("StockInventory")
