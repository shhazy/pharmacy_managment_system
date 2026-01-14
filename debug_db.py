from app.database import SessionLocal, engine
from sqlalchemy import text
from app.models import Supplier, GRN

def debug_tenant(tenant_id):
    db = SessionLocal()
    try:
        print(f"--- Debugging Tenant: {tenant_id} ---")
        
        # 1. Check Search Path
        schema = f"tenant_{tenant_id}"
        db.execute(text(f"SET search_path TO {schema}, public"))
        print(f"Set search_path to {schema}, public")
        
        # 2. Check Tables Existence
        tables = db.execute(text(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema}'")).fetchall()
        print("Tables in schema:", [t[0] for t in tables])
        
        target_table = 'purchase_conversion_units'
        has_table = target_table in [t[0] for t in tables]
        
        print(f"Has {target_table} table: {has_table}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Test for tenant t8
    debug_tenant("t8")
