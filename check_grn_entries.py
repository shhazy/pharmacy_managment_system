from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def check_entries(subdomain):
    schema = f"tenant_{subdomain}"
    with engine.connect() as conn:
        print(f"--- Checking entries for {schema} ---")
        try:
            conn.execute(text(f"SET search_path TO {schema}"))
            
            # Check GRNs
            result = conn.execute(text("SELECT id, custom_grn_no, net_total, created_at FROM grns ORDER BY created_at DESC LIMIT 5;"))
            grns = result.fetchall()
            print(f"\nRecent GRNs:")
            for g in grns:
                print(f"ID: {g[0]}, No: {g[1]}, Total: {g[2]}, Date: {g[3]}")
                
            # Check Journal Entries
            result = conn.execute(text("SELECT id, entry_number, entry_date, transaction_type, total_debit, is_posted FROM journal_entries WHERE entry_number LIKE 'JE-PUR-%' ORDER BY id DESC LIMIT 5;"))
            je = result.fetchall()
            print(f"\nRecent Purchase Journal Entries:")
            for j in je:
                print(f"ID: {j[0]}, No: {j[1]}, Date: {j[2]}, Type: {j[3]}, Amount: {j[4]}, Posted: {j[5]}")
                
            # Check Supplier Ledger
            result = conn.execute(text("SELECT id, supplier_id, transaction_type, credit_amount, balance FROM supplier_ledger ORDER BY id DESC LIMIT 5;"))
            sl = result.fetchall()
            print(f"\nRecent Supplier Ledger Entries:")
            for s in sl:
                print(f"ID: {s[0]}, Supplier: {s[1]}, Type: {s[2]}, Cr: {s[3]}, Bal: {s[4]}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_entries("tj")
