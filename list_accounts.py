from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def list_accounts(schema):
    query = text(f"SELECT account_code, account_name, account_type FROM {schema}.accounts")
    with engine.connect() as conn:
        try:
            results = conn.execute(query).fetchall()
            print(f"Accounts in {schema}:")
            for row in results:
                print(f"  {row[0]} | {row[1]} | {row[2]}")
        except Exception as e:
            print(f"Error in {schema}: {e}")

if __name__ == "__main__":
    list_accounts('tenant_tk')
