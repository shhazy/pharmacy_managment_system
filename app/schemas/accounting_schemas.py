from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

# Enums
class AccountType(str, Enum):
    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    EXPENSE = "Expense"

class TransactionType(str, Enum):
    SALE = "Sale"
    PURCHASE = "Purchase"
    PAYMENT = "Payment"
    RECEIPT = "Receipt"
    ADJUSTMENT = "Adjustment"
    OPENING = "Opening"
    CLOSING = "Closing"

class ReferenceType(str, Enum):
    INVOICE = "Invoice"
    GRN = "GRN"
    PAYMENT = "Payment"
    RECEIPT = "Receipt"
    MANUAL = "Manual"

class PaymentMethod(str, Enum):
    CASH = "Cash"
    BANK = "Bank"
    CARD = "Card"
    CHEQUE = "Cheque"

class PayeeType(str, Enum):
    SUPPLIER = "Supplier"
    EMPLOYEE = "Employee"
    CUSTOMER = "Customer"
    OTHER = "Other"

# Account Schemas
class AccountBase(BaseModel):
    account_code: str
    account_name: str
    account_type: AccountType
    parent_account_id: Optional[int] = None
    is_active: bool = True
    opening_balance: Decimal = Decimal('0.00')
    description: Optional[str] = None

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    account_name: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class AccountResponse(AccountBase):
    id: int
    current_balance: Decimal
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Journal Entry Line Schemas
class JournalEntryLineBase(BaseModel):
    account_id: int
    debit_amount: Decimal = Decimal('0.00')
    credit_amount: Decimal = Decimal('0.00')
    description: Optional[str] = None
    line_number: int
    
    @validator('debit_amount', 'credit_amount')
    def validate_amounts(cls, v):
        if v < 0:
            raise ValueError('Amount cannot be negative')
        return v
    
    @validator('credit_amount')
    def validate_debit_or_credit(cls, v, values):
        debit = values.get('debit_amount', Decimal('0.00'))
        if (debit > 0 and v > 0) or (debit == 0 and v == 0):
            raise ValueError('Either debit or credit must be greater than zero, but not both')
        return v

class JournalEntryLineCreate(JournalEntryLineBase):
    pass

class JournalEntryLineResponse(JournalEntryLineBase):
    id: int
    journal_entry_id: int
    account_name: Optional[str] = None
    
    class Config:
        from_attributes = True

# Journal Entry Schemas
class JournalEntryBase(BaseModel):
    entry_date: date
    transaction_type: TransactionType
    reference_type: ReferenceType
    reference_id: Optional[int] = None
    description: Optional[str] = None
    is_posted: bool = True

class JournalEntryCreate(JournalEntryBase):
    lines: List[JournalEntryLineCreate]
    
    @validator('lines')
    def validate_balanced_entry(cls, v):
        total_debit = sum(line.debit_amount for line in v)
        total_credit = sum(line.credit_amount for line in v)
        if total_debit != total_credit:
            raise ValueError(f'Entry is not balanced. Debit: {total_debit}, Credit: {total_credit}')
        if len(v) < 2:
            raise ValueError('Journal entry must have at least 2 lines')
        return v

class JournalEntryResponse(JournalEntryBase):
    id: int
    entry_number: str
    total_debit: Decimal
    total_credit: Decimal
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    lines: List[JournalEntryLineResponse] = []
    
    class Config:
        from_attributes = True

# Payment Voucher Schemas
class PaymentVoucherBase(BaseModel):
    payment_date: date
    payment_method: PaymentMethod
    payee_type: PayeeType
    payee_id: Optional[int] = None
    amount: Decimal
    account_id: int
    description: Optional[str] = None
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than zero')
        return v

class PaymentVoucherCreate(PaymentVoucherBase):
    pass

class PaymentVoucherResponse(PaymentVoucherBase):
    id: int
    voucher_number: str
    journal_entry_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Receipt Voucher Schemas
class ReceiptVoucherBase(BaseModel):
    receipt_date: date
    receipt_method: PaymentMethod
    payer_type: PayeeType
    payer_id: Optional[int] = None
    amount: Decimal
    account_id: int
    description: Optional[str] = None
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than zero')
        return v

class ReceiptVoucherCreate(ReceiptVoucherBase):
    pass

class ReceiptVoucherResponse(ReceiptVoucherBase):
    id: int
    voucher_number: str
    journal_entry_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Ledger Schemas
class SupplierLedgerResponse(BaseModel):
    id: int
    supplier_id: int
    transaction_date: date
    transaction_type: TransactionType
    reference_number: Optional[str] = None
    debit_amount: Decimal
    credit_amount: Decimal
    balance: Decimal
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class CustomerLedgerResponse(BaseModel):
    id: int
    patient_id: int
    transaction_date: date
    transaction_type: TransactionType
    reference_number: Optional[str] = None
    debit_amount: Decimal
    credit_amount: Decimal
    balance: Decimal
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Report Schemas
class TrialBalanceItem(BaseModel):
    account_code: str
    account_name: str
    account_type: AccountType
    debit_balance: Decimal
    credit_balance: Decimal

class TrialBalanceReport(BaseModel):
    as_of_date: date
    items: List[TrialBalanceItem]
    total_debit: Decimal
    total_credit: Decimal

class GeneralLedgerItem(BaseModel):
    date: date
    entry_number: str
    description: Optional[str]
    debit_amount: Decimal
    credit_amount: Decimal
    balance: Decimal

class GeneralLedgerReport(BaseModel):
    account_code: str
    account_name: str
    from_date: date
    to_date: date
    opening_balance: Decimal
    closing_balance: Decimal
    transactions: List[GeneralLedgerItem]

class BalanceSheetItem(BaseModel):
    account_name: str
    amount: Decimal

class BalanceSheetReport(BaseModel):
    as_of_date: date
    assets: List[BalanceSheetItem]
    liabilities: List[BalanceSheetItem]
    equity: List[BalanceSheetItem]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal

class IncomeStatementItem(BaseModel):
    account_name: str
    amount: Decimal

class IncomeStatementReport(BaseModel):
    from_date: date
    to_date: date
    revenue: List[IncomeStatementItem]
    expenses: List[IncomeStatementItem]
    total_revenue: Decimal
    total_expenses: Decimal
    net_profit: Decimal

class SupplierLedgerReport(BaseModel):
    supplier_id: int
    supplier_name: str
    from_date: date
    to_date: date
    opening_balance: Decimal
    closing_balance: Decimal
    transactions: List[SupplierLedgerResponse]

class PurchaseRegisterItem(BaseModel):
    id: int
    grn_number: str
    date: date
    supplier_name: str
    invoice_number: Optional[str]
    amount: Decimal
    payment_mode: str

class PurchaseRegisterReport(BaseModel):
    from_date: date
    to_date: date
    items: List[PurchaseRegisterItem]
    total_amount: Decimal

class SalesRegisterItem(BaseModel):
    invoice_number: str
    date: date
    customer_name: Optional[str]
    payment_method: str
    sub_total: Decimal
    discount: Decimal
    tax: Decimal
    net_total: Decimal
    status: str

class SalesRegisterReport(BaseModel):
    from_date: date
    to_date: date
    sales: List[SalesRegisterItem]
    total_sales: Decimal
    total_returns: Decimal
    net_sales: Decimal

class DayBookEntryLine(BaseModel):
    account_code: str
    account_name: str
    debit_amount: Decimal
    credit_amount: Decimal
    description: Optional[str]

class DayBookEntry(BaseModel):
    entry_number: str
    entry_date: date
    transaction_type: str
    description: Optional[str]
    total_debit: Decimal
    total_credit: Decimal
    lines: List[DayBookEntryLine]

class DayBookReport(BaseModel):
    from_date: date
    to_date: date
    entries: List[DayBookEntry]
    total_entries: int

class AgingBucket(BaseModel):
    entity_id: int
    entity_name: str
    total_balance: Decimal
    current: Decimal
    days_30: Decimal = Field(..., alias="30_days")
    days_60: Decimal = Field(..., alias="60_days")
    days_90: Decimal = Field(..., alias="90_days")
    over_90_days: Decimal

    class Config:
        allow_population_by_field_name = True

class AgingReport(BaseModel):
    as_of_date: date
    report_type: str # AP or AR
    items: List[AgingBucket]
    total_amount: Decimal
