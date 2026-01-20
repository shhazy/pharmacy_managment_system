import sys
import os
from sqlalchemy import text, inspect
from app.database import SessionLocal, engine, Base
from app.models.public_models import Tenant

def fix_all_tenant_schemas():
    db = SessionLocal()
    try:
        # 1. Get all tenants
        db.execute(text("SET search_path TO public"))
        tenants = db.query(Tenant).all()
        print(f"Found {len(tenants)} tenants to check/fix.")

        for tenant in tenants:
            schema = tenant.schema_name
            print(f"\n[+] Processing Tenant: {tenant.subdomain} (Schema: {schema})")
            
            with engine.connect() as conn:
                # Set search path to tenant specific schema
                conn.execute(text(f"SET search_path TO {schema}"))
                
                # A. Ensure accounting and ledger tables exist in the tenant schema
                # Filter Base.metadata for tables that should be in tenant (not public)
                tenant_tables = [t for t in Base.metadata.sorted_tables if t.schema != "public"]
                
                print(f" Checking/Creating missing tables in {schema}...")
                Base.metadata.create_all(bind=conn, tables=tenant_tables)
                
                # B. Add missing columns to existing tables (Hot Patch)
                patches = [
                    ("suppliers", "created_by", "INTEGER"),
                    ("suppliers", "updated_by", "INTEGER"),
                    ("suppliers", "created_at", "TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
                    ("suppliers", "updated_at", "TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
                    ("suppliers", "is_active", "BOOLEAN DEFAULT TRUE"),
                    
                    ("patients", "created_at", "TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
                    ("patients", "updated_at", "TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
                    ("patients", "is_active", "BOOLEAN DEFAULT TRUE"),
                    
                    ("invoices", "created_by", "INTEGER"),
                    ("invoices", "updated_by", "INTEGER"),
                    ("invoices", "updated_at", "TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
                ]
                
                for table, column, col_type in patches:
                    try:
                        sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"
                        conn.execute(text(sql))
                        # print(f"  - Verified/Added {column} to {table}")
                    except Exception as e:
                        print(f"  [!] Patch error on {table}.{column}: {e}")
                
                conn.commit()
                print(f" [✓] Schema {schema} is now aligned.")

        print("\n[✓] All tenant schemas processed successfully.")

    except Exception as e:
        print(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix_all_tenant_schemas()
