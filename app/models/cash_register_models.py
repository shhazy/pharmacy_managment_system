from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Boolean, Numeric, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

# --- CASH REGISTER MODELS ---

class CashRegister(Base):
    """Physical cash register/drawer"""
    __tablename__ = "cash_registers"
    
    id = Column(Integer, primary_key=True, index=True)
    register_code = Column(String(50), unique=True, nullable=False, index=True)
    register_name = Column(String(100), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    location = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("CashRegisterSession", back_populates="register")
    store = relationship("Store")

class CashRegisterSession(Base):
    """Individual shift session for a cash register"""
    __tablename__ = "cash_register_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_number = Column(String(50), unique=True, nullable=False, index=True)
    register_id = Column(Integer, ForeignKey("cash_registers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    
    # Opening Details
    opened_at = Column(DateTime, nullable=False)
    opening_float = Column(Numeric(15, 2), nullable=False)
    opening_notes = Column(Text, nullable=True)
    
    # Closing Details
    closed_at = Column(DateTime, nullable=True)
    closing_counted_cash = Column(Numeric(15, 2), nullable=True)
    closing_withdrawn = Column(Numeric(15, 2), default=0)
    expected_cash = Column(Numeric(15, 2), nullable=True)
    variance = Column(Numeric(15, 2), nullable=True)
    closing_notes = Column(Text, nullable=True)
    
    # Status: open, closed, reconciled
    status = Column(String(20), default='open', index=True)
    
    # Approval for variances
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Variance journal entry (if variance exists)
    variance_journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    register = relationship("CashRegister", back_populates="sessions")
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    store = relationship("Store")
    denomination_counts = relationship("CashDenominationCount", back_populates="session", cascade="all, delete-orphan")
    cash_movements = relationship("CashMovement", back_populates="session", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="cash_register_session")
    sales_returns = relationship("SalesReturn", back_populates="cash_register_session")
    variance_journal_entry = relationship("JournalEntry", foreign_keys=[variance_journal_entry_id])

class CashDenominationCount(Base):
    """Denomination breakdown for opening/closing counts"""
    __tablename__ = "cash_denomination_counts"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("cash_register_sessions.id"), nullable=False)
    count_type = Column(String(20), nullable=False)  # 'opening' or 'closing'
    
    # Pakistani Rupee denominations
    notes_5000 = Column(Integer, default=0)
    notes_1000 = Column(Integer, default=0)
    notes_500 = Column(Integer, default=0)
    notes_100 = Column(Integer, default=0)
    notes_50 = Column(Integer, default=0)
    notes_20 = Column(Integer, default=0)
    notes_10 = Column(Integer, default=0)
    notes_5 = Column(Integer, default=0)
    notes_1 = Column(Integer, default=0)
    
    coins_5 = Column(Integer, default=0)
    coins_2 = Column(Integer, default=0)
    coins_1 = Column(Integer, default=0)
    
    total_amount = Column(Numeric(15, 2), nullable=False)
    counted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    counted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("CashRegisterSession", back_populates="denomination_counts")
    counter = relationship("User")

class CashMovement(Base):
    """Non-sale cash movements (deposits, withdrawals, petty cash)"""
    __tablename__ = "cash_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("cash_register_sessions.id"), nullable=False)
    movement_type = Column(String(20), nullable=False)  # 'deposit', 'withdrawal', 'petty_cash'
    amount = Column(Numeric(15, 2), nullable=False)
    reason = Column(Text, nullable=True)
    reference_number = Column(String(50), nullable=True)
    
    # Link to accounting
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("CashRegisterSession", back_populates="cash_movements")
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    journal_entry = relationship("JournalEntry")
