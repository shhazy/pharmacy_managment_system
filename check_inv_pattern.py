from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
engine = create_engine(DATABASE_URL)

def check_inv():
    with engine.connect() as conn:
        print("Checking tenant_tk for INV- pattern")
        res = conn.execute(text("SELECT invoice_number FROM tenant_tk.invoices WHERE invoice_number LIKE 'INV-%' ORDER BY id DESC LIMIT 5"))
        for row in res:
            print(f"  Found: {row[0]}")
            
        print("Checking max matching pattern")
        res = conn.execute(text("SELECT MAX(invoice_number) FROM tenant_tk.invoices WHERE invoice_number LIKE 'INV-0%'"))
        print(f"  Max (approx): {res.first()[0]}")

if __name__ == "__main__":
    check_inv()
