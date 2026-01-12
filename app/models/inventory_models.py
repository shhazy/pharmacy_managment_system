from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

# Base audit fields mixin
class AuditMixin:
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

# --- INVENTORY MANAGEMENT MODELS ---

class LineItem(Base, AuditMixin):
    __tablename__ = "line_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class SubCategory(Base, AuditMixin):
    __tablename__ = "sub_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", foreign_keys=[category_id])

class ProductGroup(Base, AuditMixin):
    __tablename__ = "product_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class CategoryGroup(Base, AuditMixin):
    __tablename__ = "category_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class Generic(Base, AuditMixin):
    __tablename__ = "generics"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class CalculateSeason(Base, AuditMixin):
    __tablename__ = "calculate_seasons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class Rack(Base, AuditMixin):
    __tablename__ = "racks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class PurchaseConversionUnit(Base, AuditMixin):
    __tablename__ = "purchase_conversion_units"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
