from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def find_all_tables_named(table_name):
    query = text("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_name = :table_name
    """)
    with engine.connect() as conn:
        results = conn.execute(query, {"table_name": table_name}).fetchall()
        print(f"Occurrences of table '{table_name}':")
        for row in results:
            print(f"  Schema: {row[0]}")

if __name__ == "__main__":
    find_all_tables_named('stock_adjustments')
    # Also check for case variations if any?
    find_all_tables_named('Stock Adjustment') 
