from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def check_grn_tax(subdomain):
    schema = f"tenant_{subdomain}"
    print(f"--- Checking GRN in {schema} ---")
    
    with engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {schema}"))
        
        # specific GRN from screenshot
        result = conn.execute(text(f"SELECT id, custom_grn_no, sub_total, purchase_tax, advance_tax, discount, net_total FROM grns ORDER BY created_at DESC LIMIT 5")).fetchall()
        
        for row in result:
             print(f"GRN: {row[1]} | Sub: {row[2]} | PTax: {row[3]} | AdvTax: {row[4]} | Net: {row[6]}")

if __name__ == "__main__":
    check_grn_tax("tj")
