from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import GRN
from app.services.accounting_service import AccountingService
from datetime import datetime, date
from decimal import Decimal
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def re_record_transaction(grn_id, subdomain):
    schema = f"tenant_{subdomain}"
    print(f"--- Re-recording Transaction for GRN ID {grn_id} in {schema} ---")
    
    with engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {schema}, public"))
        
        # We need a proper session for ORM
        db = SessionLocal()
        # Set search path on session connection
        db.execute(text(f"SET search_path TO {schema}, public"))
        
        try:
            grn = db.query(GRN).filter(GRN.id == grn_id).first()
            if not grn:
                print(f"GRN {grn_id} not found.")
                return

            print(f"Loaded GRN {grn.custom_grn_no}: Net Total {grn.net_total}, Tax {grn.advance_tax}")
            
            # Check if JE exists and delete it (dangerous in prod, ok for dev fix)
            # Find JE by reference
            je_ref = f"Purchase - GRN #{grn.custom_grn_no} ({grn.payment_mode})"
            existing_je = db.execute(text(f"SELECT id FROM journal_entries WHERE reference_id = {grn.id} AND transaction_type = 'PURCHASE'")).fetchone()
            
            if existing_je:
                print(f"Found existing JE ID {existing_je[0]}. Deleting for re-record...")
                # Delete lines first
                db.execute(text(f"DELETE FROM journal_entry_lines WHERE journal_entry_id = {existing_je[0]}"))
                db.execute(text(f"DELETE FROM journal_entries WHERE id = {existing_je[0]}"))
                db.commit()
                print("Deleted old JE.")
            
            # Re-record
            print("Calling record_purchase_transaction...")
            entry = AccountingService.record_purchase_transaction(db, grn)
            print(f"Success! Created JE ID {entry.id}")
            
            # Verify lines
            lines = db.execute(text(f"SELECT COUNT(*) FROM journal_entry_lines WHERE journal_entry_id = {entry.id}")).scalar()
            print(f"New JE has {lines} lines.")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()

if __name__ == "__main__":
    # Use the ID of the GRN we inspected ealier (ID 12 or 13 had 510 total, maybe tax?)
    # Let's try ID 11 which had 110 total.
    re_record_transaction(11, "tj")
