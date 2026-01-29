from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def debug_enum():
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO tenant_t1"))
        result = conn.execute(text("SELECT account_type FROM accounts LIMIT 1;"))
        row = result.fetchone()
        if row:
            print(f"Value: '{row[0]}', Type: {type(row[0])}")
        else:
            print("No accounts found in tenant_t1")

if __name__ == "__main__":
    debug_enum()
