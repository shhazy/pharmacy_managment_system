from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def check_lines(subdomain):
    schema = f"tenant_{subdomain}"
    print(f"--- Checking Journal Entry Lines for {schema} ---")
    
    with engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {schema}"))
        
        # Get latest Purchase Journal Entry
        je = conn.execute(text("SELECT id, entry_number, total_debit, total_credit FROM journal_entries WHERE transaction_type = 'PURCHASE' ORDER BY id DESC LIMIT 1")).fetchone()
        
        if je:
            print(f"Latest JE: ID {je[0]} | {je[1]} | Dr {je[2]} | Cr {je[3]}")
            
            # Get lines
            lines = conn.execute(text(f"""
                SELECT l.id, l.account_id, a.account_name, a.account_code, l.debit_amount, l.credit_amount, l.description
                FROM journal_entry_lines l
                JOIN accounts a ON l.account_id = a.id
                WHERE l.journal_entry_id = {je[0]}
                ORDER BY l.line_number
            """)).fetchall()
            
            print(f"Found {len(lines)} lines:")
            for l in lines:
                print(f" - Line {l[0]}: {l[2]} ({l[3]}) | Dr {l[4]} | Cr {l[5]} | {l[6]}")
        else:
            print("No Purchase JE found.")

if __name__ == "__main__":
    check_lines("tj")
