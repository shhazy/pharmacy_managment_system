import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
print(f"DEBUG: Using DATABASE_URL={DATABASE_URL}")
engine = create_engine(DATABASE_URL)

def inspect_table(schema, table):
    query = text(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = '{table}' AND table_schema = '{schema}'
    """)
    with engine.connect() as conn:
        results = conn.execute(query).fetchall()
        print(f"Table: {schema}.{table}")
        if not results:
            print("  Table not found or no columns.")
        for row in results:
            print(f"  {row[0]}: {row[1]}")

if __name__ == "__main__":
    inspect_table('tenant_tk', 'stock_adjustments')
    inspect_table('public', 'stock_adjustments')
