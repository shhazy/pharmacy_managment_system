from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
engine = create_engine(DATABASE_URL)

def check_table_schema(schema, table_name):
    with engine.connect() as conn:
        print(f"Checking {schema}.{table_name}")
        result = conn.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table 
            AND table_schema = :schema
        """), {"table": table_name, "schema": schema})
        
        columns = [row[0] for row in result]
        print(f"Columns: {columns}")
        return columns

if __name__ == "__main__":
    t_schema = "tenant_tk"
    for s in [t_schema, "public"]:
        print("="*30)
        check_table_schema(s, "invoices")
        check_table_schema(s, "invoice_items")
