from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
engine = create_engine(DATABASE_URL)

def verify_query():
    with engine.connect() as conn:
        print("Testing refined invoice number query...")
        # Simulating: Invoice.invoice_number.like('INV-0%')).order_by(Invoice.invoice_number.desc()).first()
        res = conn.execute(text("SELECT invoice_number FROM tenant_tk.invoices WHERE invoice_number LIKE 'INV-0%' ORDER BY invoice_number DESC LIMIT 1"))
        row = res.first()
        if row:
            print(f"  Found: {row[0]}")
            import re
            match = re.search(r'INV-(\d+)', row[0])
            if match:
                num = int(match.group(1))
                print(f"  Next would be: INV-{(num + 1):06d}")
        else:
            print("  No matching invoice found.")

if __name__ == "__main__":
    verify_query()
