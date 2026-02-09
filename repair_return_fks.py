from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def repair_fks():
    with engine.connect() as conn:
        # Get all schemas
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'"))
        schemas = [row[0] for row in result]
        
        for schema in schemas:
            print(f"Repairing schema: {schema}")
            
            # 1. Drop the incorrect FK if it exists
            # We need to find the constraint name. It's usually 'sale_return_items_product_id_fkey'
            conn.execute(text(f"ALTER TABLE {schema}.sale_return_items DROP CONSTRAINT IF EXISTS sale_return_items_product_id_fkey"))
            
            # 2. Add the correct FK
            print(f"  Adding correct FK to {schema}.products for {schema}.sale_return_items")
            conn.execute(text(f"ALTER TABLE {schema}.sale_return_items ADD CONSTRAINT sale_return_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES {schema}.products(id)"))

        conn.commit()
    print("Repair complete.")

if __name__ == "__main__":
    repair_fks()
