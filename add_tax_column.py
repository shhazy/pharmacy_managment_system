import sys
import os
# Adjust path to include backend root
sys.path.append(os.getcwd())
from app.database import engine
from sqlalchemy import text

def add_column():
    print("Connecting to database...")
    with engine.connect() as conn:
        # Get all schemas + public
        schemas_res = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog')")).fetchall()
        schema_names = [s[0] for s in schemas_res]
        
        # Include 'public' definitely (though it's usually in listing)
        if 'public' not in schema_names:
            schema_names.append('public')
            
        print(f"Schemas found: {schema_names}")
        
        for schema in schema_names:
            print(f"Checking schema: {schema}")
            try:
                # Check if column exists
                check_sql = text(f"SELECT column_name FROM information_schema.columns WHERE table_schema='{schema}' AND table_name='products' AND column_name='tax_percent'")
                exists = conn.execute(check_sql).fetchone()
                
                if not exists:
                    print(f"Adding tax_percent to {schema}.products")
                    conn.execute(text(f"ALTER TABLE {schema}.products ADD COLUMN tax_percent FLOAT DEFAULT 0.0"))
                    conn.commit()
                else:
                    print(f"Column tax_percent already exists in {schema}.products")
            except Exception as e:
                print(f"Skipping {schema} (Error or table missing): {e}")

if __name__ == "__main__":
    add_column()
