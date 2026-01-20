from sqlalchemy import text
from app.database import engine, SessionLocal

def check_accounts():
    db = SessionLocal()
    tenant_schema = "tenant_tb"
    try:
        print(f"--- Checking Accounts in {tenant_schema} ---")
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        
        res = db.execute(text("SELECT account_code FROM accounts")).all()
        for r in res:
            print(f"  Code: {r[0]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_accounts()
