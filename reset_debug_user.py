from sqlalchemy import create_engine, text
from app.auth import get_password_hash
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def check_user():
    schema = "tenant_tj"
    with engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {schema}"))
        
        # Check user
        result = conn.execute(text("SELECT username, email FROM users")).fetchall()
        print(f"Users in {schema}: {result}")
        
        # Reset password for tj_admin to 'password123'
        hashed = get_password_hash("password123")
        conn.execute(text("UPDATE users SET hashed_password = :h WHERE username = 'tj_admin'"), {"h": hashed})
        conn.commit()
        print("Reset password for tj_admin to 'password123'")

if __name__ == "__main__":
    check_user()
