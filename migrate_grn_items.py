from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def migrate_db():
    with engine.connect() as conn:
        # Get all schemas
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'public');"))
        schemas = [row[0] for row in result]
        
        for schema in schemas:
            print(f"Migrating schema: {schema}")
            try:
                # Check if column exists first to avoid errors
                check_result = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{schema}' AND table_name = 'grn_items' AND column_name = 'foc_quantity';"))
                if not check_result.fetchone():
                    print(f"Adding foc_quantity to {schema}.grn_items")
                    conn.execute(text(f"ALTER TABLE {schema}.grn_items ADD COLUMN foc_quantity INTEGER DEFAULT 0;"))
                    conn.commit()
                    print(f"✓ Added foc_quantity to {schema}.grn_items")
                else:
                    print(f"✓ foc_quantity already exists in {schema}.grn_items")
            except Exception as e:
                print(f"Error migrating {schema}: {e}")

if __name__ == "__main__":
    migrate_db()
