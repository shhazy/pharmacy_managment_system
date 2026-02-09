from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def migrate():
    with engine.connect() as conn:
        # Get all schemas
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'"))
        schemas = [row[0] for row in result]
        
        for schema in schemas:
            print(f"Migrating schema: {schema}")
            
            # 1. Update sales_returns table
            # Check if refund_amount exists (to rename it or handle it)
            check_refund = text(f"SELECT 1 FROM information_schema.columns WHERE table_schema='{schema}' AND table_name='sales_returns' AND column_name='refund_amount'")
            if conn.execute(check_refund).fetchone():
                print(f"  Renaming refund_amount to net_total in {schema}.sales_returns")
                conn.execute(text(f"ALTER TABLE {schema}.sales_returns RENAME COLUMN refund_amount TO net_total"))

            # Add missing columns
            new_cols = [
                ("sub_total", "FLOAT DEFAULT 0.0"),
                ("tax_amount", "FLOAT DEFAULT 0.0"),
                ("return_date", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("journal_entry_id", f"INTEGER REFERENCES {schema}.journal_entries(id)")
            ]
            
            for col_name, col_def in new_cols:
                check_col = text(f"SELECT 1 FROM information_schema.columns WHERE table_schema='{schema}' AND table_name='sales_returns' AND column_name='{col_name}'")
                if not conn.execute(check_col).fetchone():
                    print(f"  Adding {col_name} to {schema}.sales_returns")
                    conn.execute(text(f"ALTER TABLE {schema}.sales_returns ADD COLUMN {col_name} {col_def}"))

            # 2. Create sale_return_items table
            create_items = text(f"""
                CREATE TABLE IF NOT EXISTS {schema}.sale_return_items (
                    id SERIAL PRIMARY KEY,
                    sales_return_id INTEGER REFERENCES {schema}.sales_returns(id),
                    product_id INTEGER REFERENCES {schema}.products(id),
                    batch_id INTEGER REFERENCES {schema}.stock_inventory(inventory_id),
                    quantity INTEGER,
                    unit_price FLOAT,
                    total_price FLOAT
                )
            """)
            print(f"  Ensuring {schema}.sale_return_items exists")
            conn.execute(create_items)

        conn.commit()

if __name__ == "__main__":
    migrate()
