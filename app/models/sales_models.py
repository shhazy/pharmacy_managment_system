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
    medicine_id = Column(Integer, ForeignKey("products.id"))  # kept column name for compatibility
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
