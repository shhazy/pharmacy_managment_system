from sqlalchemy import create_engine, text, inspect
import os

# DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")

engine = create_engine(DATABASE_URL)

def add_column():
    with engine.connect() as conn:
        # Get all schemas
        schemas = inspect(engine).get_schema_names()
        
        # Filter typical tenant schemas if you have a naming convention, or just try all relevant ones
        # For now, let's look for 'public' and any schema that might have pharmacy_settings
        
        for schema in schemas:
            if schema in ['information_schema', 'pg_catalog', 'pg_toast']: 
                continue
                
            print(f"Checking schema: {schema}")
            
            try:
                # Check if table exists
                has_table = inspect(engine).has_table("pharmacy_settings", schema=schema)
                if has_table:
                    print(f"  Table pharmacy_settings found in {schema}")
                    
                    # Check columns
                    columns = [c['name'] for c in inspect(engine).get_columns("pharmacy_settings", schema=schema)]
                    
                    if "theme_config" not in columns:
                        print(f"  Adding theme_config to {schema}.pharmacy_settings...")
                        conn.execute(text(f"ALTER TABLE {schema}.pharmacy_settings ADD COLUMN theme_config JSONB"))
                        conn.commit()
                        print("  Done.")
                    else:
                        print("  Column theme_config already exists.")
            except Exception as e:
                print(f"  Error processing schema {schema}: {e}")

if __name__ == "__main__":
    add_column()
