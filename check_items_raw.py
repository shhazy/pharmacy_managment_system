from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
engine = create_engine(DATABASE_URL)

def check_items():
    with engine.connect() as conn:
        print("Checking ALL items for Invoice INV-000051")
        # Find the ID first
        res = conn.execute(text("SELECT id FROM tenant_tk.invoices WHERE invoice_number = 'INV-000051'")).first()
        if not res:
            print("Invoice NOT FOUND")
            return
        inv_id = res[0]
        print(f"Invoice ID: {inv_id}")
        
        items = conn.execute(text(f"SELECT * FROM tenant_tk.invoice_items WHERE invoice_id = {inv_id}")).all()
        print(f"Items found: {len(items)}")
        for item in items:
            print(f"Item: {item._mapping}")

if __name__ == "__main__":
    check_items()
