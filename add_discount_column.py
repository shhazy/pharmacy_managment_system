from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
engine = create_engine(DATABASE_URL)

def add_column():
    with engine.connect() as conn:
        # Get all schemas
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%' OR schema_name = 'public'"))
        schemas = [row[0] for row in result]
        
        for schema in schemas:
            print(f"Checking schema: {schema}")
            # Check if column exists
            check_res = conn.execute(text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'invoices' 
                AND table_schema = '{schema}' 
                AND column_name = 'invoice_discount'
            """))
            
            if not check_res.first():
                print(f"Adding invoice_discount to {schema}.invoices")
                try:
                    conn.execute(text(f"ALTER TABLE {schema}.invoices ADD COLUMN invoice_discount FLOAT DEFAULT 0.0"))
                    conn.commit()
                    print(f"Success in {schema}")
                except Exception as e:
                    print(f"Failed in {schema}: {e}")
                    conn.rollback()
            else:
                print(f"Column already exists in {schema}")

if __name__ == "__main__":
    add_column()
