from sqlalchemy import text
from app.database import SessionLocal

def check_tenant_accounts(tenant_id):
    db = SessionLocal()
    try:
        schema = f"tenant_{tenant_id}"
        print(f"Checking accounts for: {schema}")
        db.execute(text(f"SET search_path TO {schema}, public"))
        
        required_codes = ["1000", "1100", "4000", "5000", "1300", "2200", "1200", "5400"]
        for code in required_codes:
            result = db.execute(text("SELECT id, account_name FROM accounts WHERE account_code = :code"), {"code": code}).fetchone()
            if result:
                print(f"  [OK] {code}: {result.account_name}")
            else:
                print(f"  [MISSING] {code}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    tid = sys.argv[1] if len(sys.argv) > 1 else 'tk'
    check_tenant_accounts(tid)
