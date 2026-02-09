from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, DateTime, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class CustomerGroup(Base):
    __tablename__ = "customer_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)

class CustomerType(Base):
    __tablename__ = "customer_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    
    # Relationships
    type_id = Column(Integer, ForeignKey("customer_types.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("customer_groups.id"), nullable=True)
    
    # Info
    start_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    status = Column(String, nullable=True)
    marital_status = Column(String, nullable=True)
    
    # Reference
    ref_no = Column(String, nullable=True)
    ref_name = Column(String, nullable=True)
    ref_phone = Column(String, nullable=True)
    
    # Contact
    city = Column(String, nullable=True)
    area = Column(String, nullable=True)
    phone_res = Column(String, nullable=True)
    phone_off = Column(String, nullable=True)
    mobile_phone = Column(String, nullable=True)
    fax = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    comments = Column(Text, nullable=True)
    mailing_status = Column(Boolean, default=False)
    ntn_no = Column(String, nullable=True)
    gst_reg_no = Column(String, nullable=True)
    
    # Identification
    cnic = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    alt_card_no = Column(String, nullable=True)
    end_date = Column(Date, nullable=True)
    
    # Credit Info
    allow_credit = Column(Boolean, default=False)
    credit_limit = Column(Float, default=0.0)
    opening_balance = Column(Float, default=0.0)
    opening_amount = Column(Float, default=0.0)
    opening_date = Column(Date, nullable=True)
    
    # System
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    
    # Relationships
    customer_type = relationship("CustomerType")
    customer_group = relationship("CustomerGroup")
