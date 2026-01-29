from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def verify(schema):
    print(f"Verifying schema: {schema}")
    with engine.connect() as conn:
        # Check adjustments with journal_entry_id
        q = text(f"SELECT adjustment_id, adjustment_type, journal_entry_id FROM {schema}.stock_adjustments WHERE adjustment_type = 'return_to_supplier' ORDER BY created_at DESC LIMIT 5")
        results = conn.execute(q).fetchall()
        if not results:
            print("  No return_to_supplier adjustments found yet. Please create one in the UI.")
            return

        for row in results:
            print(f"  AdjID: {row[0]} | Type: {row[1]} | JournalID: {row[2]}")
            if row[2]:
                # Check journal lines
                ql = text(f"SELECT account_id, debit_amount, credit_amount, description FROM public.journal_entry_lines WHERE journal_entry_id = {row[2]}")
                lines = conn.execute(ql).fetchall()
                for line in lines:
                    print(f"    Line: Account {line[0]} | Dr: {line[1]} | Cr: {line[2]} | {line[3]}")
                
                # Check supplier ledger
                qs = text(f"SELECT supplier_id, debit_amount, balance FROM {schema}.supplier_ledger WHERE journal_entry_id = {row[2]}")
                sup = conn.execute(qs).fetchone()
                if sup:
                    print(f"    Supplier Ledger: Supplier {sup[0]} | Debit: {sup[1]} | New Balance: {sup[2]}")

if __name__ == "__main__":
    verify('tenant_tk')
