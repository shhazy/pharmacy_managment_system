
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models.cash_register_models import CashRegister, CashRegisterSession, CashDenominationCount
from app.models.user_models import User
from datetime import datetime, date

def test_open_session():
    db = SessionLocal()
    try:
        # Set search path to tenant_tk
        db.execute(text("SET search_path TO tenant_tk, public"))
        
        # Get first register
        register = db.query(CashRegister).filter(CashRegister.is_active == True).first()
        if not register:
            print("No active register found")
            return
            
        # Get first user
        user = db.query(User).first()
        if not user:
            print("No user found")
            return
            
        print(f"Using Register: {register.register_name} (ID: {register.id})")
        print(f"Using User: {user.username} (ID: {user.id})")
        
        # Try to count (replicate generate_session_number logic)
        try:
            from sqlalchemy import func
            count = db.query(CashRegisterSession).filter(
                func.date(CashRegisterSession.created_at) == date.today()
            ).count()
            print(f"Existing sessions today: {count}")
        except Exception as e:
            print(f"Error in count: {e}")
            import traceback
            traceback.print_exc()
            return

        # Try to create session
        try:
            new_session = CashRegisterSession(
                session_number=f"TEST-SES-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}",
                register_id=register.id,
                user_id=user.id,
                store_id=register.store_id or 1,
                opened_at=datetime.now(),
                opening_float=1000.00,
                status='open'
            )
            db.add(new_session)
            db.flush()
            print(f"Session created with ID: {new_session.id}")
            
            # Create denominations
            denom = CashDenominationCount(
                session_id=new_session.id,
                count_type='opening',
                notes_1000=1,
                total_amount=1000.00,
                counted_by=user.id
            )
            db.add(denom)
            db.commit()
            print("Session committed successfully")
        except Exception as e:
            print(f"Error in creation: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()

    finally:
        db.close()

if __name__ == "__main__":
    test_open_session()
