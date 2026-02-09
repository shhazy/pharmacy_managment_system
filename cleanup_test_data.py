from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
engine = create_engine(DATABASE_URL)

def cleanup():
    with engine.connect() as conn:
        print("Cleaning up tenant_tk.invoices")
        res = conn.execute(text("DELETE FROM tenant_tk.invoices WHERE invoice_number LIKE 'TEST-%'"))
        print(f"  Rows deleted: {res.rowcount}")
        conn.commit()

if __name__ == "__main__":
    cleanup()
