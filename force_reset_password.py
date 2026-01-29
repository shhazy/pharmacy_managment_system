from sqlalchemy import create_engine, text
from app.auth import get_password_hash
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def brute_force_reset():
    hashed = get_password_hash("password123")
    
    with engine.connect() as conn:
        # 1. Reset in PUBLIC (for SuperAdmin/Global)
        print("Resetting 'admin' in PUBLIC schema...")
        conn.execute(text("SET search_path TO public"))
        conn.execute(text("UPDATE users SET hashed_password = :h WHERE username = 'admin'"), {"h": hashed})
        conn.commit()
        
        # 2. Reset in TENANT_TJ
        print("Resetting 'admin' in TENANT_TJ schema...")
        conn.execute(text("SET search_path TO tenant_tj"))
        conn.execute(text("UPDATE users SET hashed_password = :h WHERE username = 'admin'"), {"h": hashed})
        conn.commit()
        
        # 3. Check Tenant Config
        conn.execute(text("SET search_path TO public"))
        t = conn.execute(text("SELECT * FROM tenants WHERE subdomain = 'tj'")).fetchone()
        print(f"Tenant Config: {t}")

if __name__ == "__main__":
    brute_force_reset()
