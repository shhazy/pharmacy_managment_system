from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def check_tables():
    with engine.connect() as conn:
        q = text("SELECT table_schema, table_name FROM information_schema.tables WHERE table_name = 'journal_entries'")
        results = conn.execute(q).fetchall()
        print("Locations of 'journal_entries' table:")
        for row in results:
            print(f"  {row[0]}.{row[1]}")

if __name__ == "__main__":
    check_tables()
