from sqlalchemy import create_engine, text
from app.database import Base, engine, SessionLocal
from app.models import Tenant

def sync_all_tenants():
    db = SessionLocal()
    try:
        # Get all tenants
        db.execute(text("SET search_path TO public"))
        tenants = db.query(Tenant).all()
        print(f"Found {len(tenants)} tenants to sync...")
        
        for tenant in tenants:
            print(f"Syncing tenant: {tenant.subdomain} (Schema: {tenant.schema_name})")
            
            with engine.connect() as conn:
                # 1. Ensure schema exists
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {tenant.schema_name}"))
                conn.execute(text(f"SET search_path TO {tenant.schema_name}"))
                
                # 2. Get tables targeting this schema
                # We filter out public tables
                tenant_tables = [t for t in Base.metadata.sorted_tables if t.schema != "public"]
                
                # 3. Create all missing tables in this schema
                Base.metadata.create_all(bind=conn, tables=tenant_tables)
                
                # 3.5 Hot patch for missing columns (since create_all doesn't alter)
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS store_id INTEGER REFERENCES stores(id)"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS image_url VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS composition TEXT"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS dosage_info TEXT"))
                    conn.execute(text("ALTER TABLE batches ADD COLUMN IF NOT EXISTS store_id INTEGER REFERENCES stores(id)"))
                    
                    # Product Definition Expansion
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS barcode VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS hsn_code VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS product_code VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS ndc VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS uom VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS pack_size VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS pack_type VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS moq INTEGER DEFAULT 1"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS max_stock INTEGER DEFAULT 1000"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS shelf_life_months INTEGER DEFAULT 24"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS gross_weight VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS dimensions VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS tax_rate FLOAT DEFAULT 0.0"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS discount_allowed BOOLEAN DEFAULT TRUE"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS max_discount FLOAT DEFAULT 0.0"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS pregnancy_category VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS lactation_safety VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS storage_conditions VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS license_number VARCHAR"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS is_cold_chain BOOLEAN DEFAULT FALSE"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS is_temp_log_required BOOLEAN DEFAULT FALSE"))
                    conn.execute(text("ALTER TABLE medicines ADD COLUMN IF NOT EXISTS description TEXT"))

                    conn.commit()
                except Exception as ex: 
                    print(f"  Patch error (ignored): {ex}")
                    conn.rollback()

                # 4. Seed Default Store if missing
                res = conn.execute(text("SELECT count(*) FROM stores")).scalar()
                if res == 0:
                    print(f"  Seeding default store for {tenant.subdomain}")
                    conn.execute(text("INSERT INTO stores (name, address, is_warehouse) VALUES ('Main Branch', 'Primary Location', false)"))
                    store_id = conn.execute(text("SELECT id FROM stores LIMIT 1")).scalar()
                    conn.execute(text(f"UPDATE users SET store_id = {store_id} WHERE store_id IS NULL"))
                    conn.execute(text(f"UPDATE batches SET store_id = {store_id} WHERE store_id IS NULL"))
                conn.commit()
            print(f"  Done with {tenant.subdomain}")
            
        print("\nAll tenants synced successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sync_all_tenants()
