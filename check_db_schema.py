from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def check_db():
    with engine.connect() as conn:
        # Get all schemas
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'public');"))
        schemas = [row[0] for row in result]
        print(f"Schemas found: {schemas}")
        
        for schema in schemas:
            print(f"\nChecking schema: {schema}")
            # Check if foc_quantity exists in grn_items
            try:
                result = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{schema}' AND table_name = 'grn_items';"))
                columns = [row[0] for row in result]
                print(f"Columns in {schema}.grn_items: {columns}")
                if 'foc_quantity' not in columns:
                    print(f"!!! MISSING foc_quantity in {schema}.grn_items")
                else:
                    print(f"✓ foc_quantity exists in {schema}.grn_items")
            except Exception as e:
                print(f"Error checking {schema}: {e}")

if __name__ == "__main__":
    check_db()
