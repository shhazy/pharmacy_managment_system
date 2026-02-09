from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
engine = create_engine(DATABASE_URL)

def add_discount_columns():
    with engine.connect() as conn:
        # Get all schemas
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%' OR schema_name = 'public'"))
        schemas = [row[0] for row in result]
        
        for schema in schemas:
            print(f"Updating schema: {schema}")
            
            # Add discount_percent column
            check = conn.execute(text(f"""
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'invoice_items' AND table_schema = '{schema}' AND column_name = 'discount_percent'
            """)).first()
            if not check:
                print(f"  Adding discount_percent to {schema}.invoice_items")
                conn.execute(text(f"ALTER TABLE {schema}.invoice_items ADD COLUMN discount_percent FLOAT DEFAULT 0.0"))
            
            # Add discount_amount column
            check = conn.execute(text(f"""
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'invoice_items' AND table_schema = '{schema}' AND column_name = 'discount_amount'
            """)).first()
            if not check:
                print(f"  Adding discount_amount to {schema}.invoice_items")
                conn.execute(text(f"ALTER TABLE {schema}.invoice_items ADD COLUMN discount_amount FLOAT DEFAULT 0.0"))
            
            conn.commit()
            print(f"  Done with {schema}")

if __name__ == "__main__":
    add_discount_columns()
    print("\nAll schemas updated successfully!")
