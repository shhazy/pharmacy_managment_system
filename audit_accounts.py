from sqlalchemy import text
from app.database import engine, SessionLocal

def audit_accounts():
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT schema_name, subdomain FROM tenants"))
        tenants = result.all()
        
        for schema, sub in tenants:
            try:
                db.execute(text(f"SET search_path TO {schema}, public"))
                count = db.execute(text("SELECT count(*) FROM accounts")).scalar()
                print(f"Tenant {sub} ({schema}): {count} accounts")
            except Exception as e:
                print(f"Tenant {sub} ({schema}): ERROR - {e}")
                db.rollback()
    except Exception as e:
        print(f"Global error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    audit_accounts()
