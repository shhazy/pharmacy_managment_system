from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User, Store, Product, StockInventory, Invoice, Patient
from app.auth import create_access_token
import datetime

client = TestClient(app)

def verify_invoice_sequence():
    db = SessionLocal()
    try:
        # 1. Setup Data
        tenant_id = "tenant_tg" # Assuming default tenant
        
        # Ensure user exists for token
        user = db.query(User).filter(User.email == "admin@example.com").first()
        if not user:
            # Create dummy user if needed, or find one
            user = db.query(User).first()
        
        if not user:
            print("Creating test user...")
            from app.auth import get_password_hash
            # Ensure store exists
            store = db.query(Store).first()
            if not store:
                store = Store(name="Test Store", address="Test Address")
                db.add(store)
                db.commit()
                
            user = User(
                username="admin_test", 
                email="admin@example.com", 
                hashed_password="fake_hash", 
                store_id=store.id
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_access_token(data={"sub": user.email, "tenant_id": tenant_id})
        headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id}

        # Ensure product and stock
        product = db.query(Product).first()
        if not product:
            product = Product(product_name="Test Product", selling_price=10.0)
            db.add(product)
            db.commit()
            
        stock = db.query(StockInventory).filter(StockInventory.product_id == product.id).first()
        if not stock or stock.quantity < 100:
            if not stock:
                stock = StockInventory(
                    product_id=product.id, store_id=1, batch_number="BATCH001", 
                    quantity=1000, selling_price=10.0, unit_cost=8.0, 
                    expiry_date=datetime.date.today()
                )
                db.add(stock)
            else:
                stock.quantity = 1000
            db.commit()

        # 2. Create Invoice 1
        payload = {
            "items": [
                {
                    "medicine_id": product.id,
                    "batch_id": stock.inventory_id,
                    "quantity": 1,
                    "unit_price": 10.0,
                    "tax_percent": 0,
                    "discount_percent": 0,
                    "discount_amount": 0
                }
            ],
            "patient_id": None,
            "customer_id": None,
            "payment_method": "Cash",
            "status": "Paid",
            "details": [],
            "discount_amount": 0
        }
        
        log("\n--- Sending Invoice 1 Request ---")
        res1 = client.post("/invoices", json=payload, headers=headers)
        if res1.status_code != 200:
            log(f"Failed Inv 1: {res1.text}")
            return
            
        inv1 = res1.json()
        num1 = inv1['invoice_number']
        log(f"Invoice 1 Number: {num1}")

        # 3. Create Invoice 2
        log("\n--- Sending Invoice 2 Request ---")
        res2 = client.post("/invoices", json=payload, headers=headers)
        if res2.status_code != 200:
            log(f"Failed Inv 2: {res2.text}")
            return
            
        inv2 = res2.json()
        num2 = inv2['invoice_number']
        log(f"Invoice 2 Number: {num2}")

        # 4. Verify Sequence
        # Expected: INV-000001, INV-000002 (or if old invoices exist, INV-XXXXXX + 1)
        
        import re
        m1 = re.search(r'INV-(\d+)', num1)
        m2 = re.search(r'INV-(\d+)', num2)
        
        if m1 and m2:
            n1 = int(m1.group(1))
            n2 = int(m2.group(1))
            if n2 == n1 + 1:
                log(f"\n[SUCCESS] Invoice number incremented correctly: {num1} -> {num2}")
            else:
                log(f"\n[FAILURE] Sequence mismatch: {num1} -> {num2}")
        else:
            log(f"\n[FAILURE] Invoice numbers format incorrect: {num1}, {num2}")
            
    except Exception as e:
        log(f"Error: {e}")
    finally:
        db.close()

def log(msg):
    with open("verify_output.txt", "a") as f:
        f.write(msg + "\n")
    print(msg)

if __name__ == "__main__":
    with open("verify_output.txt", "w") as f: f.write("Starting...\n")
    try:
        verify_invoice_sequence()
    except Exception as e:
        log(f"Global Error: {e}")
    log("Finished.")
