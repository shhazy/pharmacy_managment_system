from sqlalchemy import text
from app.database import engine, SessionLocal

def check_accounts_schema():
    db = SessionLocal()
    tenant_schema = "tenant_tb"
    try:
        print(f"--- Checking Columns in {tenant_schema}.accounts ---")
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        
        res = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = :schema AND table_name = 'accounts'
        """), {"schema": tenant_schema}).all()
        
        for r in res:
            print(f"  Column: {r[0]} ({r[1]})")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_accounts_schema()
