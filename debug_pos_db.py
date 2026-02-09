from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def check_db():
    schema = "tenant_tk"
    with engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {schema}, public"))
        
        print(f"--- Checking Products in {schema} ---")
        prods = conn.execute(text("SELECT id, product_name FROM products")).fetchall()
        for p in prods:
            print(f"ID: {p[0]}, Name: {p[1]}")
        
        print("\n--- Checking Inventory for ID 1 ---")
        inv = conn.execute(text("SELECT inventory_id, product_id, quantity FROM stock_inventory WHERE product_id = 1")).fetchall()
        for i in inv:
            print(f"InvID: {i[0]}, ProdID: {i[1]}, Qty: {i[2]}")

if __name__ == "__main__":
    check_db()
