from app.database import engine, SessionLocal, Base
# Import all models explicitly to ensure they are registered with Base.metadata
from app.models import (
    Tenant, PurchaseOrder, PurchaseOrderItem, Product, Supplier, 
    Manufacturer, Batch, Store
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
            
            # Create new tables (this handles PurchaseOrderItem if missing)
            Base.metadata.create_all(bind=engine)
            
            # Manually update existing tables with new columns if they don't exist
            # This is a safe way to handle schema evolution without full migrations
            columns_to_add = [
                ("po_no", "VARCHAR"),
                ("reference_no", "VARCHAR"),
                ("issue_date", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("delivery_date", "TIMESTAMP"),
                ("sub_total", "FLOAT DEFAULT 0.0"),
                ("total_tax", "FLOAT DEFAULT 0.0"),
                ("total_discount", "FLOAT DEFAULT 0.0"),
                ("total_amount", "FLOAT DEFAULT 0.0"),
                ("status", "VARCHAR DEFAULT 'Pending'"),
                ("notes", "TEXT"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            ]
            
            for col_name, col_type in columns_to_add:
                try:
                    db.execute(text(f"ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                except Exception as e:
                    print(f"  Warning: Could not add column {col_name}: {e}")
            
            db.commit()
            print(f"  Schema {tenant.schema_name} synced successfully.")
            
    except Exception as e:
        print(f"CRITICAL ERROR during sync: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync_schemas()
