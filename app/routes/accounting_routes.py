"""
Accounting Routes
API endpoints for accounting operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, load_only
from sqlalchemy import and_, or_, func, desc, text
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal

from ..auth import get_db_with_tenant, get_current_tenant_user
from ..models import User
from ..models.accounting_models import (
    Account, JournalEntry, JournalEntryLine, SupplierLedger,
    CustomerLedger, PaymentVoucher, ReceiptVoucher,
    AccountType, TransactionType
)
from ..schemas.accounting_schemas import (
    AccountCreate, AccountUpdate, AccountResponse,
    JournalEntryCreate, JournalEntryResponse,
    PaymentVoucherCreate, PaymentVoucherResponse,
    ReceiptVoucherCreate, ReceiptVoucherResponse,
    SupplierLedgerResponse, CustomerLedgerResponse,
    TrialBalanceReport, TrialBalanceItem,
    GeneralLedgerReport, GeneralLedgerItem,
    BalanceSheetReport, BalanceSheetItem,
    IncomeStatementReport, IncomeStatementItem,
    SupplierLedgerReport, PurchaseRegisterReport, PurchaseRegisterItem,
    SalesRegisterReport, SalesRegisterItem,
    DayBookReport, DayBookEntry, DayBookEntryLine,
    AgingReport, AgingBucket
)
from ..services.accounting_service import AccountingService

router = APIRouter(prefix="/accounting", tags=["Accounting"])

# ============================================================================
# CHART OF ACCOUNTS
# ============================================================================

@router.get("/accounts", response_model=List[AccountResponse])
def get_accounts(
    account_type: Optional[AccountType] = None,
    is_active: bool = True,
    db: Session = Depends(get_db_with_tenant)
):
    """Get all accounts or filter by type"""
    query = db.query(Account)
    
    if account_type:
        query = query.filter(Account.account_type == account_type)
    
    if is_active is not None:
        query = query.filter(Account.is_active == is_active)
    
    return query.order_by(Account.account_code).all()

@router.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(account_id: int, db: Session = Depends(get_db_with_tenant)):
    """Get account by ID"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.post("/accounts", response_model=AccountResponse)
def create_account(
    account: AccountCreate,
    db: Session = Depends(get_db_with_tenant),
    user: User = Depends(get_current_tenant_user)
):
    """Create a new account"""
    # Check if account code already exists
    existing = db.query(Account).filter(Account.account_code == account.account_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account code already exists")
    
    new_account = Account(**account.dict())
    new_account.current_balance = account.opening_balance
    
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account

@router.put("/accounts/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: int,
    account_update: AccountUpdate,
    db: Session = Depends(get_db_with_tenant),
    user: User = Depends(get_current_tenant_user)
):
    """Update an account"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    for key, value in account_update.dict(exclude_unset=True).items():
        setattr(account, key, value)
    
    db.commit()
    db.refresh(account)
    return account

# ============================================================================
# JOURNAL ENTRIES
# ============================================================================

@router.get("/journal-entries", response_model=List[JournalEntryResponse])
def get_journal_entries(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    transaction_type: Optional[TransactionType] = None,
    limit: int = 100,
    db: Session = Depends(get_db_with_tenant)
):
    """Get journal entries with filters"""
    query = db.query(JournalEntry).options(joinedload(JournalEntry.lines))
    
    if from_date:
        query = query.filter(JournalEntry.entry_date >= from_date)
    if to_date:
        query = query.filter(JournalEntry.entry_date <= to_date)
    if transaction_type:
        query = query.filter(JournalEntry.transaction_type == transaction_type)
    
    return query.order_by(desc(JournalEntry.entry_date)).limit(limit).all()

@router.get("/journal-entries/{entry_id}", response_model=JournalEntryResponse)
def get_journal_entry(entry_id: int, db: Session = Depends(get_db_with_tenant)):
    """Get journal entry by ID"""
    entry = db.query(JournalEntry).options(
        joinedload(JournalEntry.lines)
    ).filter(JournalEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    
    # Enrich lines with account names
    for line in entry.lines:
        account = db.query(Account).get(line.account_id)
        if account:
            line.account_name = account.account_name
    
    return entry

@router.post("/journal-entries", response_model=JournalEntryResponse)
def create_manual_journal_entry(
    entry: JournalEntryCreate,
    db: Session = Depends(get_db_with_tenant),
    user: User = Depends(get_current_tenant_user)
):
    """Create a manual journal entry"""
    try:
        journal_entry = AccountingService.create_journal_entry(db, entry, user.id)
        
        # Reload with relationships
        db.refresh(journal_entry)
        return journal_entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================================
# PAYMENT VOUCHERS
# ============================================================================

@router.get("/payment-vouchers", response_model=List[PaymentVoucherResponse])
def get_payment_vouchers(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db_with_tenant)
):
    """Get payment vouchers"""
    query = db.query(PaymentVoucher)
    
    if from_date:
        query = query.filter(PaymentVoucher.payment_date >= from_date)
    if to_date:
        query = query.filter(PaymentVoucher.payment_date <= to_date)
    
    return query.order_by(desc(PaymentVoucher.payment_date)).all()

@router.post("/payment-vouchers", response_model=PaymentVoucherResponse)
def create_payment_voucher(
    voucher: PaymentVoucherCreate,
    db: Session = Depends(get_db_with_tenant),
    user: User = Depends(get_current_tenant_user)
):
    """Create a payment voucher and journal entry"""
    from ..models import Supplier
    
    # Generate voucher number
    year = datetime.now().year
    last_voucher = db.query(PaymentVoucher).filter(
        PaymentVoucher.voucher_number.like(f"PV-{year}-%")
    ).order_by(desc(PaymentVoucher.id)).first()
    
    if last_voucher:
        last_num = int(last_voucher.voucher_number.split('-')[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    voucher_number = f"PV-{year}-{new_num:05d}"
    
    # Create payment voucher
    new_voucher = PaymentVoucher(
        voucher_number=voucher_number,
        **voucher.dict(),
        created_by=user.id
    )
    
    db.add(new_voucher)
    db.flush()
    
    # Create journal entry
    # Dr. Accounts Payable (or Expense)
    # Cr. Cash/Bank
    
    # Determine debit account based on payee type
    if voucher.payee_type.value == "Supplier":
        ap_account = AccountingService.get_account_by_code(db, "2000")
        debit_account_id = ap_account.id if ap_account else None
    else:
        # For other payees, use Other Expenses
        expense_account = AccountingService.get_account_by_code(db, "5500")
        debit_account_id = expense_account.id if expense_account else None
    
    if not debit_account_id:
        raise HTTPException(status_code=400, detail="Required account not found")
    
    lines = [
        JournalEntryLineCreate(
            account_id=debit_account_id,
            debit_amount=voucher.amount,
            credit_amount=Decimal('0.00'),
            description=voucher.description or f"Payment - {voucher_number}",
            line_number=1
        ),
        JournalEntryLineCreate(
            account_id=voucher.account_id,
            debit_amount=Decimal('0.00'),
            credit_amount=voucher.amount,
            description=voucher.description or f"Payment - {voucher_number}",
            line_number=2
        )
    ]
    
    entry_data = JournalEntryCreate(
        entry_date=voucher.payment_date,
        transaction_type=TransactionType.PAYMENT,
        reference_type="Payment",
        reference_id=new_voucher.id,
        description=voucher.description or f"Payment - {voucher_number}",
        lines=lines
    )
    
    journal_entry = AccountingService.create_journal_entry(db, entry_data, user.id)
    new_voucher.journal_entry_id = journal_entry.id
    
    # Update supplier ledger if applicable
    if voucher.payee_type.value == "Supplier" and voucher.payee_id:
        # Update Master Supplier Balance
        supplier = db.query(Supplier).get(voucher.payee_id)
        if supplier:
            curr_bal = Decimal(str(supplier.ledger_balance or 0.0))
            supplier.ledger_balance = float(curr_bal - voucher.amount)

        # Get current balance for ledger row
        last_entry = db.query(SupplierLedger).filter(
            SupplierLedger.supplier_id == voucher.payee_id
        ).order_by(desc(SupplierLedger.id)).first()
        
        current_balance = last_entry.balance if last_entry else Decimal('0.00')
        new_balance = current_balance - voucher.amount
        
        supplier_ledger = SupplierLedger(
            supplier_id=voucher.payee_id,
            journal_entry_id=journal_entry.id,
            transaction_date=voucher.payment_date,
            transaction_type=TransactionType.PAYMENT,
            reference_number=voucher_number,
            debit_amount=voucher.amount,
            credit_amount=Decimal('0.00'),
            balance=new_balance,
            description=voucher.description or f"Payment - {voucher_number}"
        )
        db.add(supplier_ledger)
    
    db.commit()
    db.refresh(new_voucher)
    return new_voucher

# ============================================================================
# RECEIPT VOUCHERS
# ============================================================================

@router.get("/receipt-vouchers", response_model=List[ReceiptVoucherResponse])
def get_receipt_vouchers(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db_with_tenant)
):
    """Get receipt vouchers"""
    query = db.query(ReceiptVoucher)
    
    if from_date:
        query = query.filter(ReceiptVoucher.receipt_date >= from_date)
    if to_date:
        query = query.filter(ReceiptVoucher.receipt_date <= to_date)
    
    return query.order_by(desc(ReceiptVoucher.receipt_date)).all()

@router.post("/receipt-vouchers", response_model=ReceiptVoucherResponse)
def create_receipt_voucher(
    voucher: ReceiptVoucherCreate,
    db: Session = Depends(get_db_with_tenant),
    user: User = Depends(get_current_tenant_user)
):
    """Create a receipt voucher and journal entry"""
    # Generate voucher number
    year = datetime.now().year
    last_voucher = db.query(ReceiptVoucher).filter(
        ReceiptVoucher.voucher_number.like(f"RV-{year}-%")
    ).order_by(desc(ReceiptVoucher.id)).first()
    
    if last_voucher:
        last_num = int(last_voucher.voucher_number.split('-')[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    
    voucher_number = f"RV-{year}-{new_num:05d}"
    
    # Create receipt voucher
    new_voucher = ReceiptVoucher(
        voucher_number=voucher_number,
        **voucher.dict(),
        created_by=user.id
    )
    
    db.add(new_voucher)
    db.flush()
    
    # Create journal entry
    # Dr. Cash/Bank
    # Cr. Accounts Receivable (or Revenue)
    
    # Determine credit account based on payer type
    if voucher.payer_type.value == "Customer":
        ar_account = AccountingService.get_account_by_code(db, "1200")
        credit_account_id = ar_account.id if ar_account else None
    else:
        # For other payers, use Other Income
        income_account = AccountingService.get_account_by_code(db, "4100")
        credit_account_id = income_account.id if income_account else None
    
    if not credit_account_id:
        raise HTTPException(status_code=400, detail="Required account not found")
    
    lines = [
        JournalEntryLineCreate(
            account_id=voucher.account_id,
            debit_amount=voucher.amount,
            credit_amount=Decimal('0.00'),
            description=voucher.description or f"Receipt - {voucher_number}",
            line_number=1
        ),
        JournalEntryLineCreate(
            account_id=credit_account_id,
            debit_amount=Decimal('0.00'),
            credit_amount=voucher.amount,
            description=voucher.description or f"Receipt - {voucher_number}",
            line_number=2
        )
    ]
    
    entry_data = JournalEntryCreate(
        entry_date=voucher.receipt_date,
        transaction_type=TransactionType.RECEIPT,
        reference_type="Receipt",
        reference_id=new_voucher.id,
        description=voucher.description or f"Receipt - {voucher_number}",
        lines=lines
    )
    
    journal_entry = AccountingService.create_journal_entry(db, entry_data, user.id)
    new_voucher.journal_entry_id = journal_entry.id
    
    # Update customer ledger if applicable
    if voucher.payer_type.value == "Customer" and voucher.payer_id:
        # Get current balance
        last_entry = db.query(CustomerLedger).filter(
            CustomerLedger.patient_id == voucher.payer_id
        ).order_by(desc(CustomerLedger.id)).first()
        
        current_balance = last_entry.balance if last_entry else Decimal('0.00')
        new_balance = current_balance - voucher.amount
        
        customer_ledger = CustomerLedger(
            patient_id=voucher.payer_id,
            journal_entry_id=journal_entry.id,
            transaction_date=voucher.receipt_date,
            transaction_type=TransactionType.RECEIPT,
            reference_number=voucher_number,
            debit_amount=Decimal('0.00'),
            credit_amount=voucher.amount,
            balance=new_balance,
            description=voucher.description or f"Receipt - {voucher_number}"
        )
        db.add(customer_ledger)
    
    db.commit()
    db.refresh(new_voucher)
    return new_voucher

# ============================================================================
# LEDGERS
# ============================================================================

@router.get("/supplier-ledger/{supplier_id}", response_model=List[SupplierLedgerResponse])
def get_supplier_ledger(
    supplier_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db_with_tenant)
):
    """Get supplier ledger"""
    query = db.query(SupplierLedger).filter(SupplierLedger.supplier_id == supplier_id)
    
    if from_date:
        query = query.filter(SupplierLedger.transaction_date >= from_date)
    if to_date:
        query = query.filter(SupplierLedger.transaction_date <= to_date)
    
    return query.order_by(SupplierLedger.transaction_date).all()

@router.get("/customer-ledger/{customer_id}", response_model=List[CustomerLedgerResponse])
def get_customer_ledger(
    customer_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: Session = Depends(get_db_with_tenant)
):
    """Get customer ledger"""
    query = db.query(CustomerLedger).filter(CustomerLedger.patient_id == customer_id)
    
    if from_date:
        query = query.filter(CustomerLedger.transaction_date >= from_date)
    if to_date:
        query = query.filter(CustomerLedger.transaction_date <= to_date)
    
    return query.order_by(CustomerLedger.transaction_date).all()

# ============================================================================
# REPORTS
# ============================================================================

@router.get("/reports/trial-balance", response_model=TrialBalanceReport)
def get_trial_balance(
    as_of_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db_with_tenant)
):
    """Generate Trial Balance report"""
    if not as_of_date:
        as_of_date = date.today()
    
    accounts = db.query(Account).filter(Account.is_active == True).all()
    
    items = []
    total_debit = Decimal('0.00')
    total_credit = Decimal('0.00')
    
    for account in accounts:
        # Calculate balance as of date
        balance = AccountingService.get_account_balance(db, account.id, as_of_date)
        
        if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            # Normal debit balance: positive balance is debit, negative is credit
            debit_balance = balance if balance >= 0 else Decimal('0.00')
            credit_balance = abs(balance) if balance < 0 else Decimal('0.00')
        else:
            # Normal credit balance: positive balance is credit, negative is debit
            credit_balance = balance if balance >= 0 else Decimal('0.00')
            debit_balance = abs(balance) if balance < 0 else Decimal('0.00')
        
        # SUCCESS: Show all accounts as requested, even with zero balance
        items.append(TrialBalanceItem(
            account_code=account.account_code,
            account_name=account.account_name,
            account_type=account.account_type,
            debit_balance=debit_balance,
            credit_balance=credit_balance
        ))
        
        total_debit += debit_balance
        total_credit += credit_balance
    
    return TrialBalanceReport(
        as_of_date=as_of_date,
        items=items,
        total_debit=total_debit,
        total_credit=total_credit
    )

@router.get("/reports/general-ledger/{account_id}", response_model=GeneralLedgerReport)
def get_general_ledger(
    account_id: int,
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db_with_tenant)
):
    """Generate General Ledger report for an account"""
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Get opening balance (balance before from_date)
    opening_date = from_date - timedelta(days=1)
    opening_balance = AccountingService.get_account_balance(db, account_id, opening_date)
    
    # Get all journal entry lines for this account within the range
    lines = db.query(JournalEntryLine).join(JournalEntry).filter(
        and_(
            JournalEntryLine.account_id == account_id,
            JournalEntry.entry_date >= from_date,
            JournalEntry.entry_date <= to_date,
            JournalEntry.is_posted == True
        )
    ).order_by(JournalEntry.entry_date, JournalEntry.id).all()
    
    transactions = []
    current_running_balance = opening_balance
    
    for line in lines:
        entry = line.journal_entry
        
        if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            current_running_balance += (line.debit_amount - line.credit_amount)
        else:
            current_running_balance += (line.credit_amount - line.debit_amount)
        
        transactions.append(GeneralLedgerItem(
            date=entry.entry_date,
            entry_number=entry.entry_number,
            description=line.description or entry.description,
            debit_amount=line.debit_amount,
            credit_amount=line.credit_amount,
            balance=current_running_balance
        ))
    
    return GeneralLedgerReport(
        account_code=account.account_code,
        account_name=account.account_name,
        from_date=from_date,
        to_date=to_date,
        opening_balance=opening_balance,
        closing_balance=current_running_balance,
        transactions=transactions
    )

@router.get("/reports/balance-sheet", response_model=BalanceSheetReport)
def get_balance_sheet(
    as_of_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db_with_tenant)
):
    """Generate Balance Sheet report"""
    if not as_of_date:
        as_of_date = date.today()
    
    # Get all accounts
    accounts = db.query(Account).filter(Account.is_active == True).all()
    
    assets = []
    liabilities = []
    equity = []
    
    total_assets = Decimal('0.00')
    total_liabilities = Decimal('0.00')
    total_equity = Decimal('0.00')
    
    for account in accounts:
        # Calculate balance as of date
        balance = AccountingService.get_account_balance(db, account.id, as_of_date)
        
        if account.account_type == AccountType.ASSET:
            assets.append(BalanceSheetItem(
                account_name=account.account_name,
                amount=balance
            ))
            total_assets += balance
        elif account.account_type == AccountType.LIABILITY:
            liabilities.append(BalanceSheetItem(
                account_name=account.account_name,
                amount=balance
            ))
            total_liabilities += balance
        elif account.account_type == AccountType.EQUITY:
            equity.append(BalanceSheetItem(
                account_name=account.account_name,
                amount=balance
            ))
            total_equity += balance
    
    # Calculate net profit/loss from opening until as_of_date
    revenue_accounts = db.query(Account).filter(
        Account.account_type == AccountType.REVENUE,
        Account.is_active == True
    ).all()
    
    expense_accounts = db.query(Account).filter(
        Account.account_type == AccountType.EXPENSE,
        Account.is_active == True
    ).all()
    
    total_revenue = Decimal('0.00')
    total_expenses = Decimal('0.00')

    for acc in revenue_accounts:
        total_revenue += AccountingService.get_account_balance(db, acc.id, as_of_date)
    
    for acc in expense_accounts:
        total_expenses += AccountingService.get_account_balance(db, acc.id, as_of_date)

    net_profit = total_revenue - total_expenses
    
    # Add net profit to equity
    if net_profit != 0:
        equity.append(BalanceSheetItem(
            account_name="Net Profit (Retained Earnings)",
            amount=net_profit
        ))
        total_equity += net_profit
    
    return BalanceSheetReport(
        as_of_date=as_of_date,
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity
    )

@router.get("/reports/income-statement", response_model=IncomeStatementReport)
def get_income_statement(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db_with_tenant)
):
    """Generate Income Statement (Profit & Loss) report"""
    
    # Get revenue accounts
    revenue_accounts = db.query(Account).filter(
        Account.account_type == AccountType.REVENUE,
        Account.is_active == True
    ).all()
    
    # Get expense accounts
    expense_accounts = db.query(Account).filter(
        Account.account_type == AccountType.EXPENSE,
        Account.is_active == True
    ).all()
    
    revenue_items = []
    expense_items = []
    
    total_revenue = Decimal('0.00')
    total_expenses = Decimal('0.00')
    
    for account in revenue_accounts:
        # Calculate revenue for the period
        lines = db.query(JournalEntryLine).join(JournalEntry).filter(
            and_(
                JournalEntryLine.account_id == account.id,
                JournalEntry.entry_date >= from_date,
                JournalEntry.entry_date <= to_date
            )
        ).all()
        
        period_amount = sum(line.credit_amount - line.debit_amount for line in lines)
        
        if period_amount != 0:
            revenue_items.append(IncomeStatementItem(
                account_name=account.account_name,
                amount=period_amount
            ))
            total_revenue += period_amount
    
    for account in expense_accounts:
        # Calculate expenses for the period
        lines = db.query(JournalEntryLine).join(JournalEntry).filter(
            and_(
                JournalEntryLine.account_id == account.id,
                JournalEntry.entry_date >= from_date,
                JournalEntry.entry_date <= to_date
            )
        ).all()
        
        period_amount = sum(line.debit_amount - line.credit_amount for line in lines)
        
        if period_amount != 0:
            expense_items.append(IncomeStatementItem(
                account_name=account.account_name,
                amount=period_amount
            ))
            total_expenses += period_amount
    
    net_profit = total_revenue - total_expenses
    
    return IncomeStatementReport(
        from_date=from_date,
        to_date=to_date,
        revenue=revenue_items,
        expenses=expense_items,
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        net_profit=net_profit
    )

@router.get("/reports/supplier-ledger/{supplier_id}", response_model=SupplierLedgerReport)
def get_supplier_ledger_report(
    supplier_id: int,
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db_with_tenant)
):
    """Generate Supplier Ledger report"""
    # from ..models import Supplier  # Not needed if using raw SQL for name
    supplier_name = db.execute(text("SELECT name FROM suppliers WHERE id = :id"), {"id": supplier_id}).scalar()
    if not supplier_name:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Calculate opening balance
    # Total debits and credits before from_date
    totals_before = db.query(
        func.sum(SupplierLedger.debit_amount).label('debits'),
        func.sum(SupplierLedger.credit_amount).label('credits')
    ).filter(
        and_(
            SupplierLedger.supplier_id == supplier_id,
            SupplierLedger.transaction_date < from_date
        )
    ).first()
    
    opening_balance = (totals_before.credits or Decimal('0.00')) - (totals_before.debits or Decimal('0.00'))
    
    transactions_raw = db.query(SupplierLedger).filter(
        and_(
            SupplierLedger.supplier_id == supplier_id,
            SupplierLedger.transaction_date >= from_date,
            SupplierLedger.transaction_date <= to_date
        )
    ).order_by(SupplierLedger.transaction_date, SupplierLedger.id).all()
    
    # Enrich transactions with running balance
    transactions = []
    current_bal = opening_balance
    for t in transactions_raw:
        current_bal += (t.credit_amount - t.debit_amount)
        transactions.append(SupplierLedgerResponse(
            id=t.id,
            supplier_id=t.supplier_id,
            transaction_date=t.transaction_date,
            transaction_type=t.transaction_type,
            reference_number=t.reference_number,
            debit_amount=t.debit_amount,
            credit_amount=t.credit_amount,
            balance=current_bal,
            description=t.description,
            created_at=t.created_at
        ))
    
    return SupplierLedgerReport(
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        from_date=from_date,
        to_date=to_date,
        opening_balance=opening_balance,
        closing_balance=current_bal,
        transactions=transactions
    )

@router.get("/reports/purchase-register", response_model=PurchaseRegisterReport)
def get_purchase_register(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db_with_tenant)
):
    """Generate Purchase Register report"""
    from ..models import GRN, Supplier
    
    results = db.query(GRN, Supplier.name).join(Supplier).filter(
        and_(
            GRN.created_at >= datetime.combine(from_date, datetime.min.time()),
            GRN.created_at <= datetime.combine(to_date, datetime.max.time())
        )
    ).all()
    
    items = []
    total_amount = Decimal('0.00')
    
    for grn, supplier_name in results:
        amount = Decimal(str(grn.net_total or 0.0))
        items.append(PurchaseRegisterItem(
            id=grn.id,
            grn_number=grn.custom_grn_no or f"GRN-{grn.id}",
            date=grn.created_at.date() if grn.created_at else from_date,
            supplier_name=supplier_name,
            invoice_number=grn.invoice_no,
            amount=amount,
            payment_mode=grn.payment_mode or "Credit"
        ))
        total_amount += amount
        
    return PurchaseRegisterReport(
        from_date=from_date,
        to_date=to_date,
        items=items,
        total_amount=total_amount
    )

@router.get("/reports/day-book", response_model=DayBookReport)
def get_day_book(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db_with_tenant)
):
    """Generate Day Book / Journal Register"""
    entries = db.query(JournalEntry).options(
        joinedload(JournalEntry.lines)
    ).filter(
        and_(
            JournalEntry.entry_date >= from_date,
            JournalEntry.entry_date <= to_date,
            JournalEntry.is_posted == True
        )
    ).order_by(JournalEntry.entry_date, JournalEntry.id).all()
    
    result = []
    for entry in entries:
        lines_data = []
        for line in entry.lines:
            account = db.query(Account).get(line.account_id)
            lines_data.append(DayBookEntryLine(
                account_code=account.account_code if account else "N/A",
                account_name=account.account_name if account else "Unknown",
                debit_amount=line.debit_amount,
                credit_amount=line.credit_amount,
                description=line.description
            ))
        
        result.append(DayBookEntry(
            entry_number=entry.entry_number,
            entry_date=entry.entry_date,
            transaction_type=entry.transaction_type.value,
            description=entry.description,
            total_debit=entry.total_debit,
            total_credit=entry.total_credit,
            lines=lines_data
        ))
    
    return DayBookReport(
        from_date=from_date,
        to_date=to_date,
        entries=result,
        total_entries=len(result)
    )

@router.get("/reports/sales-register", response_model=SalesRegisterReport)
def get_sales_register(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db_with_tenant)
):
    """Generate Sales Register"""
    try:
        from ..models import Invoice, Patient
        
        results = db.query(Invoice, Patient.name).outerjoin(
            Patient, Invoice.patient_id == Patient.id
        ).filter(
            and_(
                Invoice.created_at >= datetime.combine(from_date, datetime.min.time()),
                Invoice.created_at <= datetime.combine(to_date, datetime.max.time()),
                Invoice.status.in_(["Paid", "Return", "Partial", "Credit"])
            )
        ).order_by(Invoice.created_at).all()
        
        sales_data = []
        total_sales = Decimal('0.00')
        total_returns = Decimal('0.00')
        
        for invoice, patient_name in results:
            # Safe numeric conversions
            raw_net = Decimal(str(invoice.net_total or 0.0))
            sub_total = Decimal(str(invoice.sub_total or 0.0))
            discount = Decimal(str(invoice.discount_amount or 0.0))
            tax = Decimal(str(invoice.tax_amount or 0.0))
            
            current_net = raw_net
            if invoice.status == "Return":
                current_net = -abs(raw_net)
                total_returns += abs(raw_net)
            else:
                total_sales += raw_net
            
            sales_data.append(SalesRegisterItem(
                invoice_number=invoice.invoice_number or f"INV-{invoice.id}",
                date=invoice.created_at.date() if invoice.created_at else from_date,
                customer_name=patient_name or "Walk-in",
                payment_method=invoice.payment_method or "Cash",
                sub_total=sub_total,
                discount=discount,
                tax=tax,
                net_total=current_net,
                status=invoice.status or "Paid"
            ))
        
        return SalesRegisterReport(
            from_date=from_date,
            to_date=to_date,
            sales=sales_data,
            total_sales=total_sales,
            total_returns=total_returns,
            net_sales=total_sales - total_returns
        )
    except Exception as e:
        print(f"ERROR in get_sales_register: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/reports/accounts-payable-aging", response_model=AgingReport)
def get_ap_aging(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db_with_tenant)
):
    """Generate Accounts Payable Aging Report"""
    try:
        from ..models import Supplier
        
        if not as_of_date:
            as_of_date = date.today()
        
        suppliers = db.query(Supplier).all()
        aging_data = []
        total_payable = Decimal('0.00')
        
        for supplier in suppliers:
            # Get latest balance
            last_entry = db.query(SupplierLedger).filter(
                SupplierLedger.supplier_id == supplier.id,
                SupplierLedger.transaction_date <= as_of_date
            ).order_by(desc(SupplierLedger.transaction_date), desc(SupplierLedger.id)).first()
            
            if not last_entry or (last_entry.balance or 0) <= 0:
                continue
            
            balance = Decimal(str(last_entry.balance or 0.0))
            total_payable += balance
            
            # Calculate buckets
            current = Decimal('0.00')
            days_30 = Decimal('0.00')
            days_60 = Decimal('0.00')
            days_90 = Decimal('0.00')
            over_90 = Decimal('0.00')
            
            # Bucketing logic
            txns = db.query(SupplierLedger).filter(
                SupplierLedger.supplier_id == supplier.id,
                SupplierLedger.credit_amount > 0,
                SupplierLedger.transaction_date <= as_of_date
            ).order_by(desc(SupplierLedger.transaction_date)).all()
            
            remaining_balance = balance
            for txn in txns:
                if remaining_balance <= 0: break
                
                txn_credit = Decimal(str(txn.credit_amount or 0.0))
                amount_to_bucket = min(txn_credit, remaining_balance)
                days_old = (as_of_date - txn.transaction_date).days
                
                if days_old <= 30: current += amount_to_bucket
                elif days_old <= 60: days_30 += amount_to_bucket
                elif days_old <= 90: days_60 += amount_to_bucket
                elif days_old <= 120: days_90 += amount_to_bucket
                else: over_90 += amount_to_bucket
                
                remaining_balance -= amount_to_bucket
                
            aging_data.append(AgingBucket(
                entity_id=supplier.id,
                entity_name=supplier.name or "Unknown",
                total_balance=balance,
                current=current,
                days_30=days_30,
                days_60=days_60,
                days_90=days_90,
                over_90_days=over_90
            ))
        
        return AgingReport(
            as_of_date=as_of_date,
            report_type="AP",
            items=aging_data,
            total_amount=total_payable
        )
    except Exception as e:
        print(f"ERROR in get_ap_aging: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AP Aging Report generation failed: {str(e)}")

@router.get("/reports/accounts-receivable-aging", response_model=AgingReport)
def get_ar_aging(
    as_of_date: date = Query(default=None),
    db: Session = Depends(get_db_with_tenant)
):
    """Generate Accounts Receivable Aging Report"""
    try:
        from ..models import Patient
        
        if not as_of_date:
            as_of_date = date.today()
        
        patients = db.query(Patient).all()
        aging_data = []
        total_receivable = Decimal('0.00')
        
        for patient in patients:
            # Get latest balance
            last_entry = db.query(CustomerLedger).filter(
                CustomerLedger.patient_id == patient.id,
                CustomerLedger.transaction_date <= as_of_date
            ).order_by(desc(CustomerLedger.transaction_date), desc(CustomerLedger.id)).first()
            
            if not last_entry or (last_entry.balance or 0) <= 0:
                continue
            
            balance = Decimal(str(last_entry.balance or 0.0))
            total_receivable += balance
            
            # Calculate buckets
            current = Decimal('0.00')
            days_30 = Decimal('0.00')
            days_60 = Decimal('0.00')
            days_90 = Decimal('0.00')
            over_90 = Decimal('0.00')
            
            # Distribute CURRENT balance across buckets
            txns = db.query(CustomerLedger).filter(
                CustomerLedger.patient_id == patient.id,
                CustomerLedger.debit_amount > 0,
                CustomerLedger.transaction_date <= as_of_date
            ).order_by(desc(CustomerLedger.transaction_date)).all()
            
            remaining_balance = balance
            for txn in txns:
                if remaining_balance <= 0: break
                
                txn_debit = Decimal(str(txn.debit_amount or 0.0))
                amount_to_bucket = min(txn_debit, remaining_balance)
                days_old = (as_of_date - txn.transaction_date).days
                
                if days_old <= 30: current += amount_to_bucket
                elif days_old <= 60: days_30 += amount_to_bucket
                elif days_old <= 90: days_60 += amount_to_bucket
                elif days_old <= 120: days_90 += amount_to_bucket
                else: over_90 += amount_to_bucket
                
                remaining_balance -= amount_to_bucket
            
            aging_data.append(AgingBucket(
                entity_id=patient.id,
                entity_name=patient.name or "Unknown",
                total_balance=balance,
                current=current,
                days_30=days_30,
                days_60=days_60,
                days_90=days_90,
                over_90_days=over_90
            ))
        
        return AgingReport(
            as_of_date=as_of_date,
            report_type="AR",
            items=aging_data,
            total_amount=total_receivable
        )
    except Exception as e:
        print(f"ERROR in get_ar_aging: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AR Aging Report generation failed: {str(e)}")

