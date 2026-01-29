import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
TENANT_ID = "tk" # Using tenant_tk

def simulate_return():
    # 1. Login to get token (assuming standard dev credentials)
    # If login is required, we'd do it here. For now, let's assume we can try to call the endpoint 
    # if it's open or we have a hardcoded token.
    # Alternatively, use SQLAlchemy directly for zero-dependency test.
    pass

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def test_via_orm():
    db = SessionLocal()
    try:
        # Set search path
        db.execute(text("SET search_path TO tenant_tk, public"))
        
        # 1. Find an inventory record with a supplier and cost
        stock = db.execute(text("SELECT inventory_id, product_id, batch_number, quantity, unit_cost, supplier_id FROM tenant_tk.stock_inventory WHERE quantity > 10 AND supplier_id IS NOT NULL LIMIT 1")).fetchone()
        
        if not stock:
            print("No suitable inventory found for test.")
            return
            
        print(f"Testing with Stock ID: {stock[0]} | Product: {stock[1]} | Qty: {stock[3]} | Cost: {stock[4]}")
        
        # 2. Simulate the API call logic by calling the service (or just the route logic)
        # For simplicity, let's just create the adjustment and then manually trigger the accounting service
        from app.models.procurement_models import StockAdjustment
        from app.services.accounting_service import AccountingService
        
        adj = StockAdjustment(
            product_id=stock[1],
            batch_number=stock[2],
            inventory_id=stock[0],
            adjustment_type="return_to_supplier",
            quantity_adjusted=-1.0, # Return 1 unit
            previous_quantity=stock[3],
            new_quantity=stock[3] - 1.0,
            reason="Test Return",
            status="approved"
        )
        db.add(adj)
        db.commit()
        db.refresh(adj)
        
        print(f"Created Adjustment ID: {adj.adjustment_id}")
        
        # 3. Call Accounting
        AccountingService.record_inventory_adjustment_accounting(db, adj, 1) # User ID 1
        
        print(f"Accounting recorded. Journal ID: {adj.journal_entry_id}")
        
        # 4. Verify Journal Entry exists
        if adj.journal_entry_id:
            je = db.execute(text(f"SELECT entry_number, total_debit FROM journal_entries WHERE id = {adj.journal_entry_id}")).fetchone()
            print(f"  Verified Journal: {je[0]} | Amount: {je[1]}")
            
            lines = db.execute(text(f"SELECT account_id, debit_amount, credit_amount FROM public.journal_entry_lines WHERE journal_entry_id = {adj.journal_entry_id}")).fetchall()
            for l in lines:
                print(f"    - Account {l[0]} | Dr: {l[1]} | Cr: {l[2]}")
                
            ledger = db.execute(text(f"SELECT id, balance FROM tenant_tk.supplier_ledger WHERE journal_entry_id = {adj.journal_entry_id}")).fetchone()
            if ledger:
                print(f"  Verified Supplier Ledger Entry: {ledger[0]} | New Balance: {ledger[1]}")
        else:
            print("FAILED: No Journal ID linked to adjustment.")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_via_orm()
