from sqlalchemy import create_engine, text
from app.database import SessionLocal, engine
from app.models import Tenant, User, Role
import traceback

def debug_login():
    db = SessionLocal()
    tenant_id = "test"
    
    try:
        tenant = db.query(Tenant).filter(Tenant.subdomain == tenant_id).first()
        if not tenant:
            print(f"Tenant {tenant_id} not found")
            return

        db.execute(text(f"SET search_path TO {tenant.schema_name}, public"))
        
        users = db.query(User).all()
        print(f"Found {len(users)} users in {tenant_id}")
        
        for user in users:
            print(f"Checking user: {user.username} (ID: {user.id})")
            
            # 1. Check Password field
            print(f"  PWD Hash len: {len(user.hashed_password) if user.hashed_password else 'None'}")
            
            # 2. Check Store ID
            print(f"  Store ID: {user.store_id}")
            
            # 3. Check Roles (This triggers the join)
            try:
                roles = user.roles
                role_names = [r.name for r in roles]
                print(f"  Roles: {role_names}")
            except Exception as e:
                print(f"  !! Roles access failed: {e}")
                traceback.print_exc()

    except Exception as e:
        print("\n!!! EXCEPTION CAUGHT !!!")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_login()
