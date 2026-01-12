from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from datetime import datetime
from ..database import Base

# --- SERVICES & LOGS ---

class TemperatureLog(Base):
    __tablename__ = "temperature_logs"
    id = Column(Integer, primary_key=True, index=True)
    fridge_id = Column(String)
    temperature = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class RegulatoryLog(Base):
    __tablename__ = "regulatory_logs"
    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("products.id"))  # kept column name for compatibility
    action = Column(String) # Dispensed, Received
    quantity = Column(Integer)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"))
    change_qty = Column(Integer) # Negative for damage/waste, Positive for corrections
    reason = Column(String) # Waste, Expiry, Damage, Correction
    created_at = Column(DateTime, default=datetime.utcnow)
