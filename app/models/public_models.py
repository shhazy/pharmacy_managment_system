from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from ..database import Base

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
    is_trial = Column(Boolean, default=False)
    trial_end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SuperAdmin(Base):
    __tablename__ = "superadmins"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class SoftwarePayment(Base):
    __tablename__ = "software_payments"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True)
    receipt_path = Column(String) # Path to uploaded receipt
    valid_from = Column(DateTime)
    valid_to = Column(DateTime)
    status = Column(String, default="pending") # pending, approved, rejected
    rejection_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
