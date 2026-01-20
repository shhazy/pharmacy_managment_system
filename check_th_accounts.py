from sqlalchemy import text
from app.database import engine, SessionLocal

def check_accounts():
    db = SessionLocal()
    tenant_schema = "tenant_th"
    try:
        print(f"--- Checking Accounts in {tenant_schema} ---")
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        
        # USE account_code and account_name
        res = db.execute(text("SELECT id, account_code, account_name FROM accounts WHERE account_code IN ('1000', '1300', '2000')")).all()
        for r in res:
            print(f"  Account: ID={r[0]}, Code={r[1]}, Name={r[2]}")
        
        if len(res) < 3:
            print(f"\n[MISSING] Found only {len(res)} of 3 required accounts.")
            missing = set(['1000', '1300', '2000']) - set([r[1] for r in res])
            print(f"  Missing codes: {missing}")
        else:
            print("\n[OK] All required accounts exist.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_accounts()
