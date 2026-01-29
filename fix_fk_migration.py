from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def fix_migration():
    with engine.connect() as conn:
        # Get all schemas
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'"))
        schemas = [row[0] for row in result]
        
        for schema in schemas:
            print(f"Fixing schema: {schema}")
            # Identify the constraint name (usually stock_adjustments_journal_entry_id_fkey)
            # OR just drop it by name if we are sure
            try:
                # Drop existing FK if it points to public
                # We'll try to find the constraint name first
                find_constraint = text(f"""
                    SELECT constraint_name 
                    FROM information_schema.key_column_usage 
                    WHERE table_name = 'stock_adjustments' 
                    AND table_schema = '{schema}' 
                    AND column_name = 'journal_entry_id'
                """)
                constraint_name = conn.execute(find_constraint).scalar()
                
                if constraint_name:
                    print(f"  Dropping constraint {constraint_name}")
                    conn.execute(text(f"ALTER TABLE {schema}.stock_adjustments DROP CONSTRAINT {constraint_name}"))
                
                # Add correct FK
                print(f"  Adding correct FK to {schema}.journal_entries")
                conn.execute(text(f"ALTER TABLE {schema}.stock_adjustments ADD CONSTRAINT stock_adjustments_journal_entry_id_fkey FOREIGN KEY (journal_entry_id) REFERENCES {schema}.journal_entries(id)"))
            except Exception as e:
                print(f"  Error in {schema}: {e}")
        
        conn.commit()

if __name__ == "__main__":
    fix_migration()
