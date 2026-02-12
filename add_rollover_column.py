from sqlalchemy import create_engine, text
from app.core.config import settings

def add_column():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        try:
            # Check if column exists first to be safe
            check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='cash_register_sessions' AND column_name='closing_withdrawn'")
            result = conn.execute(check_sql).fetchone()
            
            if not result:
                print("Adding closing_withdrawn column...")
                conn.execute(text("ALTER TABLE cash_register_sessions ADD COLUMN closing_withdrawn NUMERIC(15, 2) DEFAULT 0"))
                conn.commit()
                print("Column added successfully.")
            else:
                print("Column already exists.")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    add_column()
