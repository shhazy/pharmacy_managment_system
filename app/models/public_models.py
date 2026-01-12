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
    created_at = Column(DateTime, default=datetime.utcnow)

class SuperAdmin(Base):
    __tablename__ = "superadmins"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
