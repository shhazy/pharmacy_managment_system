from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from datetime import datetime
from ..database import Base

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
    medicine_id = Column(Integer, ForeignKey("products.id"))  # kept column name for compatibility
    quantity = Column(Integer)
    status = Column(String, default="Sent")
    created_at = Column(DateTime, default=datetime.utcnow)
