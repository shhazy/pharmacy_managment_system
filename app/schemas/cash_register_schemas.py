from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# --- CASH REGISTER SCHEMAS ---

class CashRegisterBase(BaseModel):
    register_code: str
    register_name: str
    store_id: Optional[int] = None
    location: Optional[str] = None

class CashRegisterCreate(CashRegisterBase):
    pass

class CashRegisterUpdate(BaseModel):
    register_name: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None

class CashRegister(CashRegisterBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- DENOMINATION SCHEMAS ---

class DenominationCountBase(BaseModel):
    notes_5000: int = 0
    notes_1000: int = 0
    notes_500: int = 0
    notes_100: int = 0
    notes_50: int = 0
    notes_20: int = 0
    notes_10: int = 0
    notes_5: int = 0
    notes_1: int = 0
    coins_5: int = 0
    coins_2: int = 0
    coins_1: int = 0

class DenominationCountCreate(DenominationCountBase):
    count_type: str  # 'opening' or 'closing'
    total_amount: Decimal

class DenominationCount(DenominationCountCreate):
    id: int
    session_id: int
    counted_by: Optional[int] = None
    counted_at: datetime
    
    class Config:
        from_attributes = True

# --- CASH MOVEMENT SCHEMAS ---

class CashMovementBase(BaseModel):
    movement_type: str  # 'deposit', 'withdrawal', 'petty_cash'
    amount: Decimal
    reason: Optional[str] = None
    reference_number: Optional[str] = None

class CashMovementCreate(CashMovementBase):
    session_id: int

class CashMovement(CashMovementBase):
    id: int
    session_id: int
    journal_entry_id: Optional[int] = None
    created_by: int
    approved_by: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- SESSION SCHEMAS ---

class CashRegisterSessionBase(BaseModel):
    register_id: int
    opening_float: Decimal
    opening_notes: Optional[str] = None

class CashRegisterSessionOpen(CashRegisterSessionBase):
    opening_denominations: DenominationCountBase

class CashRegisterSessionClose(BaseModel):
    closing_counted_cash: Decimal
    closing_withdrawn: Optional[Decimal] = Decimal(0)
    closing_notes: Optional[str] = None
    closing_denominations: DenominationCountBase

class CashRegisterSessionApprove(BaseModel):
    approval_notes: Optional[str] = None

class CashRegisterSession(BaseModel):
    id: int
    session_number: str
    register_id: int
    user_id: int
    store_id: int
    
    opened_at: datetime
    opening_float: Decimal
    opening_notes: Optional[str] = None
    
    closed_at: Optional[datetime] = None
    closing_counted_cash: Optional[Decimal] = None
    closing_withdrawn: Optional[Decimal] = Decimal(0)
    expected_cash: Optional[Decimal] = None
    variance: Optional[Decimal] = None
    closing_notes: Optional[str] = None
    
    status: str
    
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    
    variance_journal_entry_id: Optional[int] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CashRegisterSessionDetail(CashRegisterSession):
    """Extended session info with related data"""
    register: Optional[CashRegister] = None
    opening_denomination: Optional[DenominationCount] = None
    closing_denomination: Optional[DenominationCount] = None
    cash_movements: List[CashMovement] = []
    
    # Summary fields
    total_cash_sales: Optional[Decimal] = None
    total_card_sales: Optional[Decimal] = None
    total_credit_sales: Optional[Decimal] = None
    total_sales: Optional[Decimal] = None
    total_cash_returns: Optional[Decimal] = None
    total_deposits: Optional[Decimal] = None
    total_withdrawals: Optional[Decimal] = None
    cash_in_flow: Optional[Decimal] = None
    cash_out_flow: Optional[Decimal] = None
    cash_in_hand: Optional[Decimal] = None
    sales_count: Optional[int] = None
    returns_count: Optional[int] = None

# --- SHIFT SUMMARY SCHEMA ---

class ShiftSummary(BaseModel):
    session: CashRegisterSessionDetail
    
    # Financial summary
    opening_float: Decimal
    cash_sales: Decimal
    card_sales: Decimal
    credit_sales: Decimal
    total_sales: Decimal
    cash_returns: Decimal
    deposits: Decimal
    withdrawals: Decimal
    expected_cash: Decimal
    counted_cash: Decimal
    variance: Decimal
    cash_in_flow: Decimal
    cash_out_flow: Decimal
    
    # Transaction counts
    sales_count: int
    returns_count: int
    movements_count: int
    
    # Cashier info
    cashier_name: str
    register_name: str
    store_name: Optional[str] = None
