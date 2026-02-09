from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
engine = create_engine(DATABASE_URL)

def fix_schemas():
    with engine.connect() as conn:
        # Get all schemas
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%' OR schema_name = 'public'"))
        schemas = [row[0] for row in result]
        
        for schema in schemas:
            print(f"Fixing schema: {schema}")
            
            # --- INVOICES TABLE ---
            invoice_cols = {
                'customer_id': 'INTEGER',
                'invoice_discount': 'FLOAT DEFAULT 0.0'
            }
            
            for col, col_type in invoice_cols.items():
                check = conn.execute(text(f"""
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'invoices' AND table_schema = '{schema}' AND column_name = '{col}'
                """)).first()
                if not check:
                    print(f"  Adding {col} to {schema}.invoices")
                    conn.execute(text(f"ALTER TABLE {schema}.invoices ADD COLUMN {col} {col_type}"))
            
            # --- INVOICE_ITEMS TABLE ---
            item_cols = {
                'retail_price': 'FLOAT',
                'tax_amount': 'FLOAT DEFAULT 0.0'
            }
            
            for col, col_type in item_cols.items():
                check = conn.execute(text(f"""
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'invoice_items' AND table_schema = '{schema}' AND column_name = '{col}'
                """)).first()
                if not check:
                    print(f"  Adding {col} to {schema}.invoice_items")
                    conn.execute(text(f"ALTER TABLE {schema}.invoice_items ADD COLUMN {col} {col_type}"))
            
            conn.commit()
            print(f"  Done with {schema}")

if __name__ == "__main__":
    fix_schemas()
