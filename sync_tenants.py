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
            print(f"\n[SYNC] Tenant: {tenant.subdomain} (Schema: {tenant.schema_name})")
            
            try:
                with engine.connect() as conn:
                    # 1. Ensure schema exists
                    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {tenant.schema_name}"))
                    conn.execute(text(f"SET search_path TO {tenant.schema_name}"))
                    conn.commit() # Commit schema creation
                    
                    # 2. Get tables targeting this schema
                    tenant_tables = [t for t in Base.metadata.sorted_tables if t.schema != "public"]
                    
                    # 3. Create/Update tables
                    Base.metadata.create_all(bind=conn, tables=tenant_tables)
                    conn.commit()
                    
                    # 4. Patch Columns (Robustly with individual commits if needed)
                    patches = [
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS store_id INTEGER REFERENCES stores(id)",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS image_url VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS composition TEXT",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS dosage_info TEXT",
                        "ALTER TABLE batches ADD COLUMN IF NOT EXISTS store_id INTEGER REFERENCES stores(id)",
                        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS created_by INTEGER",
                        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS updated_by INTEGER",
                        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP",
                        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP",
                        "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
                        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP",
                        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP",
                        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
                        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS created_by INTEGER",
                        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS updated_by INTEGER",
                        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS barcode VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS hsn_code VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS product_code VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS ndc VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS uom VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS pack_size VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS pack_type VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS moq INTEGER DEFAULT 1",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS max_stock INTEGER DEFAULT 1000",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS shelf_life_months INTEGER DEFAULT 24",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS gross_weight VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS dimensions VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS tax_rate FLOAT DEFAULT 0.0",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS discount_allowed BOOLEAN DEFAULT TRUE",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS max_discount FLOAT DEFAULT 0.0",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS pregnancy_category VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS lactation_safety VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS storage_conditions VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS license_number VARCHAR",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS is_cold_chain BOOLEAN DEFAULT FALSE",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS is_temp_log_required BOOLEAN DEFAULT FALSE",
                        "ALTER TABLE medicines ADD COLUMN IF NOT EXISTS description TEXT",
                        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS cash_register_session_id INTEGER REFERENCES cash_register_sessions(id)",
                        "ALTER TABLE sales_returns ADD COLUMN IF NOT EXISTS cash_register_session_id INTEGER REFERENCES cash_register_sessions(id)"
                    ]
                    
                    for p in patches:
                        try:
                            conn.execute(text(p))
                            conn.commit()
                        except Exception as e:
                            # print(f"    Patch skipped: {e}")
                            conn.rollback()

                    # 5. Seed Default Store
                    res = conn.execute(text("SELECT count(*) FROM stores")).scalar()
                    if res == 0:
                        print(f"    Seeding default store")
                        conn.execute(text("INSERT INTO stores (name, address, is_warehouse) VALUES ('Main Branch', 'Primary Location', false)"))
                        conn.commit()
                    
                    # 6. Seed COA
                    default_accounts = [
                        {"code": "1000", "name": "Cash", "type": "ASSET"},
                        {"code": "1100", "name": "Bank Account", "type": "ASSET"},
                        {"code": "1200", "name": "Accounts Receivable", "type": "ASSET"},
                        {"code": "1300", "name": "Inventory", "type": "ASSET"},
                        {"code": "1400", "name": "Prepaid Expenses", "type": "ASSET"},
                        {"code": "1500", "name": "Fixed Assets", "type": "ASSET"},
                        {"code": "2000", "name": "Accounts Payable", "type": "LIABILITY"},
                        {"code": "3000", "name": "Owner's Capital", "type": "EQUITY"},
                        {"code": "4000", "name": "Sales Revenue", "type": "REVENUE"},
                        {"code": "5000", "name": "Cost of Goods Sold", "type": "EXPENSE"},
                        {"code": "5400", "name": "Discount Given", "type": "EXPENSE"},
                    ]
                    
                    for acc in default_accounts:
                        exists = conn.execute(text("SELECT id FROM accounts WHERE account_code = :code"), {"code": acc["code"]}).first()
                        if not exists:
                            print(f"    Seeding account {acc['code']}")
                            conn.execute(text("""
                                INSERT INTO accounts (account_code, account_name, account_type, is_active, opening_balance, current_balance, description)
                                VALUES (:code, :name, :type, true, 0.0, 0.0, :desc)
                            """), {
                                "code": acc["code"],
                                "name": acc["name"],
                                "type": acc["type"],
                                "desc": f"Default {acc['type']} account"
                            })
                            conn.commit()
                
                print(f"  [DONE] {tenant.subdomain}")
            except Exception as e:
                print(f"  [ERROR] Failed syncing tenant {tenant.subdomain}: {e}")
            
        print("\nAll tenants process completed.")
    except Exception as e:
        print(f"Global Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sync_all_tenants()
