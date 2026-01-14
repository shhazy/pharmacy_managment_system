from app.database import engine, SessionLocal, Base
# Import all models explicitly to ensure they are registered with Base.metadata
from app.models import (
    Tenant, PurchaseOrder, PurchaseOrderItem, Product, Supplier, 
    Manufacturer, Batch, Store, GRN, GRNItem
)
from sqlalchemy import text
import sys

def sync_schemas():
    db = SessionLocal()
    try:
        # Debug: Print registered tables
        print("Registered tables in Base.metadata:", Base.metadata.tables.keys())

        # 1. Update public schema
        print("Syncing public schema...")
        db.execute(text("SET search_path TO public"))
        Base.metadata.create_all(bind=engine)
        
        # 2. Get all tenants
        tenants = db.query(Tenant).all()
        
        for tenant in tenants:
            print(f"Syncing tenant: {tenant.name} (schema: {tenant.schema_name})...")
            # Set search path for current session
            db.execute(text(f"SET search_path TO {tenant.schema_name}"))
            
            # Create new tables (GRN, GRNItem)
            Base.metadata.create_all(bind=engine)
            
            db.commit()
            print(f"  Schema {tenant.schema_name} synced successfully.")
            
    except Exception as e:
        print(f"CRITICAL ERROR during sync: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync_schemas()
