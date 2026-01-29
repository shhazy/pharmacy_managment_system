from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def check_columns_everywhere(table_name):
    query = text("""
        SELECT table_schema, column_name 
        FROM information_schema.columns 
        WHERE table_name = :table_name
    """)
    with engine.connect() as conn:
        results = conn.execute(query, {"table_name": table_name}).fetchall()
        schemas = {}
        for row in results:
            if row[0] not in schemas:
                schemas[row[0]] = []
            schemas[row[0]].append(row[1])
        
        for schema, columns in schemas.items():
            print(f"Schema: {schema}")
            if 'adjustment_id' not in columns:
                print(f"  !!! MISSING adjustment_id. Columns: {columns}")
            else:
                print(f"  OK. Has adjustment_id.")

if __name__ == "__main__":
    check_columns_everywhere('stock_adjustments')
