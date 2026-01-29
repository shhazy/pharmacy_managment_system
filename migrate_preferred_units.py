from sqlalchemy import create_engine, text, inspect
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")

def add_preferred_units_columns(schema):
    print(f"Checking schema: {schema}")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {schema}, public"))
        
        # Check if columns exist
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns("products", schema=schema)]
        
        if "preferred_purchase_unit_id" not in columns:
            print(f"  > Adding 'preferred_purchase_unit_id' to {schema}.products...")
            conn.execute(text(f"""
                ALTER TABLE {schema}.products 
                ADD COLUMN preferred_purchase_unit_id INTEGER 
                REFERENCES {schema}.purchase_conversion_units(id);
            """))
            print("  ✓ Added preferred_purchase_unit_id.")
        else:
            print("  ✓ preferred_purchase_unit_id already exists.")
            
        if "preferred_pos_unit_id" not in columns:
            print(f"  > Adding 'preferred_pos_unit_id' to {schema}.products...")
            conn.execute(text(f"""
                ALTER TABLE {schema}.products 
                ADD COLUMN preferred_pos_unit_id INTEGER 
                REFERENCES {schema}.purchase_conversion_units(id);
            """))
            print("  ✓ Added preferred_pos_unit_id.")
        else:
            print("  ✓ preferred_pos_unit_id already exists.")

        conn.commit()

if __name__ == "__main__":
    add_preferred_units_columns('tenant_th')
