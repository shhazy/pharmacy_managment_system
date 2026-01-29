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
            # Check if column exists
            check_query = text(f"""
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'stock_adjustments' 
                AND table_schema = '{schema}' 
                AND column_name = 'journal_entry_id'
            """)
            if not conn.execute(check_query).fetchone():
                print(f"  Adding journal_entry_id to {schema}.stock_adjustments")
                conn.execute(text(f"ALTER TABLE {schema}.stock_adjustments ADD COLUMN journal_entry_id INTEGER REFERENCES public.journal_entries(id)"))
            else:
                print(f"  journal_entry_id already exists in {schema}.stock_adjustments")
        
        conn.commit()

if __name__ == "__main__":
    migrate()
