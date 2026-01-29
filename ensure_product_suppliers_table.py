from sqlalchemy import create_engine, text, inspect
from app.database import Base
from app.models.pharmacy_models import ProductSupplier
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")

def ensure_table(schema):
    print(f"Checking schema: {schema}")
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    # Set search path to check table existence in schema
    with engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {schema}, public"))
        if not inspector.has_table("product_suppliers", schema=schema):
            print(f"  > Table 'product_suppliers' missing in {schema}. Creating...")
            ProductSupplier.__table__.create(conn)
            conn.commit()
            print("  ✓ Created.")
        else:
            print("  ✓ Table exists.")

if __name__ == "__main__":
    ensure_table('tenant_th')
