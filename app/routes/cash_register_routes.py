from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, text
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from ..database import get_db
from ..auth import get_current_tenant_user, get_db_with_tenant
from ..models.cash_register_models import (
    CashRegister, CashRegisterSession, CashDenominationCount, CashMovement
)
from ..models.sales_models import Invoice, SalesReturn
from ..models.accounting_models import JournalEntry, JournalEntryLine, Account
from ..auth import get_current_tenant_user, get_db_with_tenant
from ..models.user_models import User, Store
from ..schemas.cash_register_schemas import (
    CashRegisterCreate, CashRegisterUpdate, CashRegister as CashRegisterSchema,
    CashRegisterSessionOpen, CashRegisterSessionClose, CashRegisterSessionApprove,
    CashRegisterSession as CashRegisterSessionSchema,
    CashRegisterSessionDetail, CashMovementCreate, CashMovement as CashMovementSchema,
    ShiftSummary
)

router = APIRouter(prefix="/cash-registers", tags=["Cash Registers"])

# --- HELPER FUNCTIONS ---

def generate_session_number(db: Session) -> str:
    """Generate unique session number"""
    today = datetime.now().strftime("%Y%m%d")
    count = db.query(CashRegisterSession).filter(
        func.date(CashRegisterSession.created_at) == date.today()
    ).count()
    return f"SES-{today}-{count + 1:04d}"

def calculate_denomination_total(denom: dict) -> Decimal:
    """Calculate total from denomination breakdown"""
    total = Decimal(0)
    total += Decimal(denom.get('notes_5000', 0)) * Decimal(5000)
    total += Decimal(denom.get('notes_1000', 0)) * Decimal(1000)
    total += Decimal(denom.get('notes_500', 0)) * Decimal(500)
    total += Decimal(denom.get('notes_100', 0)) * Decimal(100)
    total += Decimal(denom.get('notes_50', 0)) * Decimal(50)
    total += Decimal(denom.get('notes_20', 0)) * Decimal(20)
    total += Decimal(denom.get('notes_10', 0)) * Decimal(10)
    total += Decimal(denom.get('notes_5', 0)) * Decimal(5)
    total += Decimal(denom.get('notes_1', 0)) * Decimal(1)
    total += Decimal(denom.get('coins_5', 0)) * Decimal(5)
    total += Decimal(denom.get('coins_2', 0)) * Decimal(2)
    total += Decimal(denom.get('coins_1', 0)) * Decimal(1)
    return total

def calculate_expected_cash(session: CashRegisterSession, db: Session) -> Decimal:
    """Calculate expected cash for a session"""
    summary = get_session_summary_data(session, db)
    return summary['cash_in_hand']

def get_session_summary_data(session: CashRegisterSession, db: Session) -> dict:
    """Calculate all summary fields for a session"""
    # Opening
    opening_float = Decimal(session.opening_float)
    
    # Sales by payment method
    sales_query = db.query(
        Invoice.payment_method, 
        func.sum(Invoice.net_total),
        func.count(Invoice.id)
    ).filter(Invoice.cash_register_session_id == session.id).group_by(Invoice.payment_method).all()
    
    cash_sales = Decimal(0)
    card_sales = Decimal(0)
    credit_sales = Decimal(0)
    sales_count = 0
    
    for method, total, count in sales_query:
        amt = Decimal(total or 0)
        sales_count += (count or 0)
        if method == 'Cash':
            cash_sales = amt
        elif method == 'Card':
            card_sales = amt
        elif method == 'Credit':
            credit_sales = amt
            
    total_sales = cash_sales + card_sales + credit_sales
    
    # Returns (Assuming all returns are cash for simplicity, or we can filter)
    # Most POS systems return cash even if sold by card, but let's check payment_method if exists on return
    cash_returns = db.query(func.sum(SalesReturn.net_total)).filter(
        SalesReturn.cash_register_session_id == session.id
    ).scalar() or Decimal(0)
    cash_returns = Decimal(cash_returns)
    
    returns_count = db.query(func.count(SalesReturn.id)).filter(
        SalesReturn.cash_register_session_id == session.id
    ).scalar() or 0
    
    # Cash Movements
    deposits = db.query(func.sum(CashMovement.amount)).filter(
        and_(
            CashMovement.session_id == session.id,
            CashMovement.movement_type == 'deposit'
        )
    ).scalar() or Decimal(0)
    deposits = Decimal(deposits)
    
    withdrawals = db.query(func.sum(CashMovement.amount)).filter(
        and_(
            CashMovement.session_id == session.id,
            CashMovement.movement_type.in_(['withdrawal', 'petty_cash'])
        )
    ).scalar() or Decimal(0)
    withdrawals = Decimal(withdrawals)
    
    movements_count = db.query(func.count(CashMovement.id)).filter(
        CashMovement.session_id == session.id
    ).scalar() or 0
    
    # Flow & Hand
    cash_in_flow = cash_sales + deposits
    cash_out_flow = cash_returns + withdrawals
    cash_in_hand = opening_float + cash_in_flow - cash_out_flow
    
    return {
        "opening_float": opening_float,
        "total_cash_sales": cash_sales,
        "total_card_sales": card_sales,
        "total_credit_sales": credit_sales,
        "total_sales": total_sales,
        "total_cash_returns": cash_returns,
        "total_deposits": deposits,
        "total_withdrawals": withdrawals,
        "cash_in_flow": cash_in_flow,
        "cash_out_flow": cash_out_flow,
        "cash_in_hand": cash_in_hand,
        "sales_count": sales_count,
        "returns_count": returns_count,
        "movements_count": movements_count
    }

def create_variance_journal_entry(
    session: CashRegisterSession,
    variance: Decimal,
    db: Session,
    user_id: int
) -> Optional[JournalEntry]:
    """Create journal entry for cash variance"""
    if variance == 0:
        return None
    
    # Get cash account (1000)
    cash_account = db.query(Account).filter(Account.account_code == "1000").first()
    if not cash_account:
        raise HTTPException(status_code=404, detail="Cash account not found")
    
    # Determine variance account based on over/short
    if variance > 0:
        # Cash Over - Credit to Other Income (4100)
        variance_account = db.query(Account).filter(Account.account_code == "4100").first()
        if not variance_account:
            raise HTTPException(status_code=404, detail="Other Income account not found")
        
        # Dr. Cash, Cr. Other Income
        lines = [
            JournalEntryLine(
                account_id=cash_account.id,
                debit_amount=abs(variance),
                credit_amount=0,
                description=f"Cash over - Session {session.session_number}",
                line_number=1
            ),
            JournalEntryLine(
                account_id=variance_account.id,
                debit_amount=0,
                credit_amount=abs(variance),
                description=f"Cash over - Session {session.session_number}",
                line_number=2
            )
        ]
    else:
        # Cash Short - Debit to Other Expenses (5500)
        variance_account = db.query(Account).filter(Account.account_code == "5500").first()
        if not variance_account:
            raise HTTPException(status_code=404, detail="Other Expenses account not found")
        
        # Dr. Other Expenses, Cr. Cash
        lines = [
            JournalEntryLine(
                account_id=variance_account.id,
                debit_amount=abs(variance),
                credit_amount=0,
                description=f"Cash short - Session {session.session_number}",
                line_number=1
            ),
            JournalEntryLine(
                account_id=cash_account.id,
                debit_amount=0,
                credit_amount=abs(variance),
                description=f"Cash short - Session {session.session_number}",
                line_number=2
            )
        ]
    
    # Create journal entry
    entry_number = f"JE-VAR-{session.session_number}"
    journal_entry = JournalEntry(
        entry_number=entry_number,
        entry_date=date.today(),
        transaction_type="Adjustment",
        reference_type="Manual",
        reference_id=session.id,
        description=f"Cash variance for session {session.session_number}",
        total_debit=abs(variance),
        total_credit=abs(variance),
        is_posted=True,
        created_by=user_id
    )
    
    db.add(journal_entry)
    db.flush()
    
    # Add lines
    for line in lines:
        line.journal_entry_id = journal_entry.id
        db.add(line)
    
    # Update account balances
    if variance > 0:
        cash_account.current_balance += abs(variance)
        variance_account.current_balance += abs(variance)
    else:
        cash_account.current_balance -= abs(variance)
        variance_account.current_balance += abs(variance)
    
    return journal_entry

# --- CASH REGISTER MANAGEMENT ---

@router.post("/", response_model=CashRegisterSchema)
def create_cash_register(
    register: CashRegisterCreate,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """Create a new cash register"""
    # Check if register code already exists
    existing = db.query(CashRegister).filter(
        CashRegister.register_code == register.register_code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Register code already exists")
    
    db_register = CashRegister(**register.dict())
    db.add(db_register)
    db.commit()
    db.execute(text(f"SET search_path TO {db.info.get('tenant_schema', 'public')}, public"))
    db.refresh(db_register)
    return db_register

@router.get("/", response_model=List[CashRegisterSchema])
def list_cash_registers(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """List all cash registers"""
    query = db.query(CashRegister)
    if active_only:
        query = query.filter(CashRegister.is_active == True)
    return query.offset(skip).limit(limit).all()

@router.get("/{register_id}", response_model=CashRegisterSchema)
def get_cash_register(
    register_id: int,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """Get cash register by ID"""
    register = db.query(CashRegister).filter(CashRegister.id == register_id).first()
    if not register:
        raise HTTPException(status_code=404, detail="Cash register not found")
    return register

@router.put("/{register_id}", response_model=CashRegisterSchema)
def update_cash_register(
    register_id: int,
    register_update: CashRegisterUpdate,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """Update cash register"""
    db_register = db.query(CashRegister).filter(CashRegister.id == register_id).first()
    if not db_register:
        raise HTTPException(status_code=404, detail="Cash register not found")
    
    update_data = register_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_register, field, value)
    
    db.commit()
    db.refresh(db_register)
    return db_register

@router.delete("/{register_id}")
def deactivate_cash_register(
    register_id: int,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """Deactivate cash register"""
    db_register = db.query(CashRegister).filter(CashRegister.id == register_id).first()
    if not db_register:
        raise HTTPException(status_code=404, detail="Cash register not found")
    
    # Check for active sessions
    active_session = db.query(CashRegisterSession).filter(
        and_(
            CashRegisterSession.register_id == register_id,
            CashRegisterSession.status == 'open'
        )
    ).first()
    if active_session:
        raise HTTPException(status_code=400, detail="Cannot deactivate register with active session")
    
    db_register.is_active = False
    db.commit()
    return {"message": "Cash register deactivated"}

# --- SESSION MANAGEMENT ---

@router.post("/sessions/open", response_model=CashRegisterSessionSchema)
def open_cash_register_session(
    session_data: CashRegisterSessionOpen,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """Open a new cash register session"""
    # Check if user already has an active session
    existing_session = db.query(CashRegisterSession).filter(
        and_(
            CashRegisterSession.user_id == current_user.id,
            CashRegisterSession.status == 'open'
        )
    ).first()
    if existing_session:
        raise HTTPException(
            status_code=400,
            detail=f"User already has an active session: {existing_session.session_number}"
        )
    
    # Verify register exists and is active
    register = db.query(CashRegister).filter(CashRegister.id == session_data.register_id).first()
    if not register or not register.is_active:
        raise HTTPException(status_code=404, detail="Cash register not found or inactive")
    
    # Calculate denomination total
    denom_dict = session_data.opening_denominations.dict()
    calculated_total = calculate_denomination_total(denom_dict)
    
    # Verify it matches opening float
    if abs(calculated_total - session_data.opening_float) > Decimal('0.01'):
        raise HTTPException(
            status_code=400,
            detail=f"Denomination total ({calculated_total}) does not match opening float ({session_data.opening_float})"
        )
    
    # Ensure store_id is present
    store_id = current_user.store_id or register.store_id
    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="User or Register is not assigned to a store. Please contact administrator."
        )

    # Create session
    session_number = generate_session_number(db)
    new_session = CashRegisterSession(
        session_number=session_number,
        register_id=session_data.register_id,
        user_id=current_user.id,
        store_id=store_id,
        opened_at=datetime.now(),
        opening_float=session_data.opening_float,
        opening_notes=session_data.opening_notes,
        status='open'
    )
    
    db.add(new_session)
    db.flush()
    
    # Create opening denomination count
    opening_denom = CashDenominationCount(
        session_id=new_session.id,
        count_type='opening',
        **denom_dict,
        total_amount=calculated_total,
        counted_by=current_user.id
    )
    db.add(opening_denom)
    
    db.commit()
    db.execute(text(f"SET search_path TO {db.info.get('tenant_schema', 'public')}, public"))
    db.refresh(new_session)
    return new_session

@router.get("/sessions/active", response_model=Optional[CashRegisterSessionDetail])
def get_active_session(
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """Get active session for current user"""
    session = db.query(CashRegisterSession).filter(
        and_(
            CashRegisterSession.user_id == current_user.id,
            CashRegisterSession.status == 'open'
        )
    ).options(
        joinedload(CashRegisterSession.register),
        joinedload(CashRegisterSession.denomination_counts),
        joinedload(CashRegisterSession.cash_movements)
    ).first()
    
    if not session:
        return None
    
    # Calculate summary fields using helper
    summary = get_session_summary_data(session, db)
    
    # Build response
    session_dict = CashRegisterSessionSchema.from_orm(session).dict()
    session_dict.update(summary)
    
    # Load related objects
    session_dict['register'] = session.register
    session_dict['cash_movements'] = session.cash_movements
    session_dict['opening_denomination'] = next(
        (d for d in session.denomination_counts if d.count_type == 'opening'), None
    )
    session_dict['closing_denomination'] = next(
        (d for d in session.denomination_counts if d.count_type == 'closing'), None
    )
    
    return session_dict

@router.get("/sessions/last-closed", response_model=Optional[CashRegisterSessionSchema])
def get_last_closed_session(
    register_id: int,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """Get the last closed session for a specific register to carry over balance"""
    session = db.query(CashRegisterSession).filter(
        and_(
            CashRegisterSession.register_id == register_id,
            CashRegisterSession.status == 'closed'
        )
    ).order_by(CashRegisterSession.closed_at.desc()).first()
    
    return session

@router.put("/sessions/{session_id}/close", response_model=CashRegisterSessionSchema)
def close_cash_register_session(
    session_id: int,
    close_data: CashRegisterSessionClose,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """Close a cash register session"""
    session = db.query(CashRegisterSession).filter(CashRegisterSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify session belongs to current user
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to close this session")
    
    # Verify session is open
    if session.status != 'open':
        raise HTTPException(status_code=400, detail="Session is not open")
    
    # Calculate denomination total
    denom_dict = close_data.closing_denominations.dict()
    calculated_total = calculate_denomination_total(denom_dict)
    
    # Verify it matches counted cash
    if abs(calculated_total - close_data.closing_counted_cash) > Decimal('0.01'):
        raise HTTPException(
            status_code=400,
            detail=f"Denomination total ({calculated_total}) does not match counted cash ({close_data.closing_counted_cash})"
        )
    
    # Calculate expected cash
    expected_cash = calculate_expected_cash(session, db)
    variance = close_data.closing_counted_cash - expected_cash
    
    # Update session
    session.closed_at = datetime.now()
    session.closing_counted_cash = close_data.closing_counted_cash
    session.closing_withdrawn = close_data.closing_withdrawn
    session.expected_cash = expected_cash
    session.variance = variance
    session.closing_notes = close_data.closing_notes
    session.status = 'closed'
    
    # Create closing denomination count
    closing_denom = CashDenominationCount(
        session_id=session.id,
        count_type='closing',
        **denom_dict,
        total_amount=calculated_total,
        counted_by=current_user.id
    )
    db.add(closing_denom)
    
    # Create variance journal entry if needed
    if abs(variance) > Decimal('0.01'):
        journal_entry = create_variance_journal_entry(session, variance, db, current_user.id)
        if journal_entry:
            session.variance_journal_entry_id = journal_entry.id
    
    db.commit()
    db.refresh(session)
    return session

@router.get("/sessions/{session_id}", response_model=CashRegisterSessionDetail)
def get_session(
    session_id: int,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """Get session details"""
    session = db.query(CashRegisterSession).filter(
        CashRegisterSession.id == session_id
    ).options(
        joinedload(CashRegisterSession.register),
        joinedload(CashRegisterSession.denomination_counts),
        joinedload(CashRegisterSession.cash_movements)
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Build detailed response
    session_dict = CashRegisterSessionSchema.from_orm(session).dict()
    session_dict['register'] = session.register
    session_dict['opening_denomination'] = next(
        (d for d in session.denomination_counts if d.count_type == 'opening'), None
    )
    session_dict['closing_denomination'] = next(
        (d for d in session.denomination_counts if d.count_type == 'closing'), None
    )
    session_dict['cash_movements'] = session.cash_movements
    
    return session_dict

@router.get("/sessions", response_model=List[CashRegisterSessionSchema])
def list_sessions(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    register_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """List cash register sessions with filters"""
    query = db.query(CashRegisterSession)
    
    if status:
        query = query.filter(CashRegisterSession.status == status)
    if user_id:
        query = query.filter(CashRegisterSession.user_id == user_id)
    if register_id:
        query = query.filter(CashRegisterSession.register_id == register_id)
    if start_date:
        query = query.filter(func.date(CashRegisterSession.opened_at) >= start_date)
    if end_date:
        query = query.filter(func.date(CashRegisterSession.opened_at) <= end_date)
    
    query = query.order_by(CashRegisterSession.opened_at.desc())
    return query.offset(skip).limit(limit).all()

# --- CASH MOVEMENTS ---

@router.post("/movements", response_model=CashMovementSchema)
def create_cash_movement(
    movement: CashMovementCreate,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """Record a cash movement (deposit/withdrawal/petty cash)"""
    # Verify session exists and is open
    session = db.query(CashRegisterSession).filter(CashRegisterSession.id == movement.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != 'open':
        raise HTTPException(status_code=400, detail="Session is not open")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this session")
    
    try:
        # Create cash movement
        db_movement = CashMovement(
            **movement.dict(),
            created_by=current_user.id
        )
        db.add(db_movement)
        db.flush() # Get the ID while session is active
        
        # Refresh while session is definitively pointing to the correct schema
        # SQLAlchemy refresh sometimes fails if the schema path is complex or reset on commit
        db.commit()
        
        # Manually fetch to be absolutely sure we avoid the "Could not refresh instance" error
        db.execute(text(f"SET search_path TO {db.info.get('tenant_schema', 'public')}, public"))
        db.refresh(db_movement)
        
        return db_movement
    except Exception as e:
        db.rollback()
        print(f"ERROR in create_cash_movement: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to record movement: {str(e)}")

@router.get("/movements", response_model=List[CashMovementSchema])
def list_cash_movements(
    session_id: Optional[int] = None,
    db: Session = Depends(get_db_with_tenant),
    current_user: User = Depends(get_current_tenant_user)
):
    """List cash movements"""
    query = db.query(CashMovement)
    if session_id:
        query = query.filter(CashMovement.session_id == session_id)
    return query.all()
