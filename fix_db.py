from app.database import engine
from sqlalchemy import text, inspect

def migrate():
    inspector = inspect(engine)
    
    # 1. Get all schemas
    with engine.connect() as conn:
        res = conn.execute(text("SELECT schema_name FROM tenants"))
        schemas = [row[0] for row in res]
        schemas.append('public')
    
    for schema in schemas:
        print(f"MIGRATING SCHEMA: {schema}")
        try:
            with engine.begin() as conn: # Use begin() for automatic commit/rollback
                conn.execute(text(f"SET search_path TO {schema}, public"))
                
                for table in ['purchase_order_items', 'grn_items']:
                    # Check columns using inspector (can use schema arg)
                    cols = [c['name'] for c in inspector.get_columns(table, schema=schema)]
                    
                    if 'purchase_conversion_unit_id' not in cols:
                        print(f"Adding purchase_conversion_unit_id to {schema}.{table}")
                        conn.execute(text(f"ALTER TABLE {schema}.{table} ADD COLUMN purchase_conversion_unit_id INTEGER REFERENCES purchase_conversion_units(id)"))
                    
                    if 'factor' not in cols:
                        print(f"Adding factor to {schema}.{table}")
                        conn.execute(text(f"ALTER TABLE {schema}.{table} ADD COLUMN factor INTEGER DEFAULT 1"))
        except Exception as e:
            print(f"Error migrating {schema}: {e}")

if __name__ == "__main__":
    migrate()
