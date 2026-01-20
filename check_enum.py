from sqlalchemy import text
from app.database import SessionLocal

def check_enum():
    db = SessionLocal()
    try:
        # Check enum labels in postgres
        res = db.execute(text("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'accounttype'::regtype")).all()
        print("Postgres Enum labels for 'accounttype':")
        for r in res:
            print(f"  {r[0]}")
    except Exception as e:
        print(f"Error checking enum: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_enum()
