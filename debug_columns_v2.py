
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_structure():
    conn = psycopg2.connect("postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
    cur = conn.cursor()
    
    schemas = ['public', 'tenant_tk']
    tables = ['invoices', 'sales_returns']
    
    print("Checking database structure...")
    for schema in schemas:
        for table in tables:
            try:
                cur.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = '{schema}' 
                    AND table_name = '{table}'
                    AND column_name = 'cash_register_session_id';
                """)
                res = cur.fetchone()
                if res:
                    print(f"[OK] {schema}.{table} HAS cash_register_session_id")
                else:
                    print(f"[MISSING] {schema}.{table} DOES NOT HAVE cash_register_session_id")
                    
                # Check all columns for that table
                cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{schema}' AND table_name = '{table}'")
                cols = [r[0] for r in cur.fetchall()]
                print(f"      Columns in {schema}.{table}: {', '.join(cols)}")
            except Exception as e:
                print(f"[ERROR] Could not check {schema}.{table}: {e}")
                conn.rollback()
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_structure()
