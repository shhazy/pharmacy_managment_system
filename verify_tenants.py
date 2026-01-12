from sqlalchemy import create_engine, text
from app.database import SessionLocal, engine
from app.models import Tenant, User
import traceback

def verify_all_tenants():
    db = SessionLocal()
    try:
        # Get all tenants from public
        db.execute(text("SET search_path TO public"))
        tenants = db.query(Tenant).all()
        print(f"Found {len(tenants)} tenants to verify.")
        
        for t in tenants:
            print(f"--- Verifying {t.subdomain} ({t.schema_name}) ---")
            try:
                db.execute(text(f"SET search_path TO {t.schema_name}, public"))
                # Try simple query
                user = db.query(User).first()
                if user:
                    print(f"  OK. Found user: {user.username}, Store ID: {user.store_id}")
                    # Force access to roles to check join
                    _ = user.roles
                else:
                    print("  OK. No users found (but query worked).")
            except Exception as e:
                print(f"  FAIL: {str(e)}")
                # traceback.print_exc() 
                db.rollback()
                
    except Exception as e:
        print(f"Global Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_all_tenants()
