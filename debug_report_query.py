from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime, time
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_report_query(subdomain):
    schema = f"tenant_{subdomain}"
    print(f"--- Checking Report Query for {schema} ---")
    
    with engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {schema}"))
        
        # Test Date Range
        today = date.today()
        # Hardcode the date seen in logs "2026-01-28"
        # The log showed 2026-01-28 07:54 UTC
        target_date = date(2026, 1, 28) 
        
        start = datetime.combine(target_date, time.min)
        end = datetime.combine(target_date, time.max)
        
        print(f"Querying range: {start} to {end}")
        
        # Test Supplier Ledger Query (Month Range)
        start_month = date(2026, 1, 1)
        end_month = date(2026, 1, 28)
        
        print(f"Checking Supplier Ledger from {start_month} to {end_month}")
        
        query = text("""
            SELECT id, supplier_id, transaction_date, transaction_type, debit_amount, credit_amount 
            FROM supplier_ledger 
            WHERE transaction_date >= :start 
            AND transaction_date <= :end
            ORDER BY transaction_date, id
        """)
        
        result = conn.execute(query, {
            "start": start_month, 
            "end": end_month
        }).fetchall()
        
        print(f"Found {len(result)} ledger entries:")
        for r in result:
            print(r)

if __name__ == "__main__":
    check_report_query("tj")
