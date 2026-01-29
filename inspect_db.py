import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
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

def delete_table(schema, table):
    print(f"Deleting table: {schema}.{table}")
    with engine.connect() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {schema}.{table} CASCADE"))
        conn.commit()

if __name__ == "__main__":
    # 1. Inspect
    inspect_table('tenant_tk', 'stock_adjustments')
    inspect_table('public', 'stock_adjustments')
    
    # 2. Delete the conflicting one in public
    delete_table('public', 'stock_adjustments')
    
    # 3. Final Inspect
    print("Post-deletion check:")
    inspect_table('public', 'stock_adjustments')
