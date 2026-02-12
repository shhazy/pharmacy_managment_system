
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_structure():
    conn = psycopg2.connect("postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
    cur = conn.cursor()
    
    schemas = ['tenant_tk']
    tables = ['cash_register_sessions', 'cash_denomination_counts', 'cash_movements', 'cash_registers']
    
    print("Checking cash register tables...")
    for schema in schemas:
        for table in tables:
            try:
                cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = '{schema}' AND table_name = '{table}'")
                cols = cur.fetchall()
                if not cols:
                    print(f"[MISSING] Table {schema}.{table} NOT FOUND")
                else:
                    print(f"[OK] {schema}.{table} columns:")
                    for col in cols:
                        print(f"      - {col[0]} ({col[1]})")
            except Exception as e:
                print(f"[ERROR] Could not check {schema}.{table}: {e}")
                conn.rollback()
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_structure()
