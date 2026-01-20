from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, ForeignKey, Enum as SQLEnum, Numeric, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base
import enum

# Enums
class AccountType(str, enum.Enum):
    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    EXPENSE = "Expense"

class TransactionType(str, enum.Enum):
    SALE = "Sale"
    PURCHASE = "Purchase"
    PAYMENT = "Payment"
    RECEIPT = "Receipt"
    ADJUSTMENT = "Adjustment"
    OPENING = "Opening"
    CLOSING = "Closing"

class ReferenceType(str, enum.Enum):
    INVOICE = "Invoice"
    GRN = "GRN"
    PAYMENT = "Payment"
    RECEIPT = "Receipt"
    MANUAL = "Manual"

class PaymentMethod(str, enum.Enum):
    CASH = "Cash"
    BANK = "Bank"
    CARD = "Card"
    CHEQUE = "Cheque"

class PayeeType(str, enum.Enum):
    SUPPLIER = "Supplier"
    EMPLOYEE = "Employee"
    CUSTOMER = "Customer"
    OTHER = "Other"

# Models
class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_code = Column(String(20), unique=True, nullable=False, index=True)
    account_name = Column(String(200), nullable=False)
    account_type = Column(SQLEnum(AccountType), nullable=False)
    parent_account_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    is_active = Column(Boolean, default=True)
    opening_balance = Column(Numeric(15, 2), default=0.0)
    current_balance = Column(Numeric(15, 2), default=0.0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent_account = relationship("Account", remote_side=[id], backref="sub_accounts")
    journal_lines = relationship("JournalEntryLine", back_populates="account")

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    entry_number = Column(String(50), unique=True, nullable=False, index=True)
    entry_date = Column(Date, nullable=False, index=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    reference_type = Column(SQLEnum(ReferenceType), nullable=False)
    reference_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    total_debit = Column(Numeric(15, 2), default=0.0)
    total_credit = Column(Numeric(15, 2), default=0.0)
    is_posted = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lines = relationship("JournalEntryLine", back_populates="journal_entry", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])
    
    __table_args__ = (
        CheckConstraint('total_debit = total_credit', name='check_balanced_entry'),
    )

class JournalEntryLine(Base):
    __tablename__ = "journal_entry_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    journal_entry_id = Column(Integer, ForeignKey('journal_entries.id'), nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    debit_amount = Column(Numeric(15, 2), default=0.0)
    credit_amount = Column(Numeric(15, 2), default=0.0)
    description = Column(Text, nullable=True)
    line_number = Column(Integer, nullable=False)
    
    # Relationships
    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="journal_lines")
    
    __table_args__ = (
        CheckConstraint('(debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0)', 
                       name='check_debit_or_credit'),
    )

class SupplierLedger(Base):
    __tablename__ = "supplier_ledger"
    
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    journal_entry_id = Column(Integer, ForeignKey('journal_entries.id'), nullable=False)
    transaction_date = Column(Date, nullable=False, index=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    reference_number = Column(String(100), nullable=True)
    debit_amount = Column(Numeric(15, 2), default=0.0)
    credit_amount = Column(Numeric(15, 2), default=0.0)
    balance = Column(Numeric(15, 2), default=0.0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    supplier = relationship("Supplier")
    journal_entry = relationship("JournalEntry")

class CustomerLedger(Base):
    __tablename__ = "customer_ledger"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    journal_entry_id = Column(Integer, ForeignKey('journal_entries.id'), nullable=False)
    transaction_date = Column(Date, nullable=False, index=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    reference_number = Column(String(100), nullable=True)
    debit_amount = Column(Numeric(15, 2), default=0.0)
    credit_amount = Column(Numeric(15, 2), default=0.0)
    balance = Column(Numeric(15, 2), default=0.0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient")
    journal_entry = relationship("JournalEntry")

class PaymentVoucher(Base):
    __tablename__ = "payment_vouchers"
    
    id = Column(Integer, primary_key=True, index=True)
    voucher_number = Column(String(50), unique=True, nullable=False, index=True)
    payment_date = Column(Date, nullable=False, index=True)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    payee_type = Column(SQLEnum(PayeeType), nullable=False)
    payee_id = Column(Integer, nullable=True)
    amount = Column(Numeric(15, 2), nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    journal_entry_id = Column(Integer, ForeignKey('journal_entries.id'), nullable=True)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    account = relationship("Account")
    journal_entry = relationship("JournalEntry")
    creator = relationship("User", foreign_keys=[created_by])

class ReceiptVoucher(Base):
    __tablename__ = "receipt_vouchers"
    
    id = Column(Integer, primary_key=True, index=True)
    voucher_number = Column(String(50), unique=True, nullable=False, index=True)
    receipt_date = Column(Date, nullable=False, index=True)
    receipt_method = Column(SQLEnum(PaymentMethod), nullable=False)
    payer_type = Column(SQLEnum(PayeeType), nullable=False)
    payer_id = Column(Integer, nullable=True)
    amount = Column(Numeric(15, 2), nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    journal_entry_id = Column(Integer, ForeignKey('journal_entries.id'), nullable=True)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    account = relationship("Account")
    journal_entry = relationship("JournalEntry")
    creator = relationship("User", foreign_keys=[created_by])
