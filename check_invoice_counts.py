from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
engine = create_engine(DATABASE_URL)

def check_counts():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%' OR schema_name = 'public'"))
        schemas = [row[0] for row in result]
        
        for schema in schemas:
            print(f"Schema: {schema}")
            try:
                res = conn.execute(text(f"SELECT count(*), max(invoice_number) FROM {schema}.invoices"))
                count, max_inv = res.first()
                print(f"  Invoices: {count}, Last Num: {max_inv}")
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    check_counts()
