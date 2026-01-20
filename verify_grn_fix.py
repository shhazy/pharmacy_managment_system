from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models import GRN, Supplier
from app.services.accounting_service import AccountingService
from datetime import date
from decimal import Decimal

def verify_fix():
    db = SessionLocal()
    tenant_schema = "tenant_tg"
    try:
        print(f"--- Verifying Fix on schema: {tenant_schema} ---")
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        
        # 1. Setup Test Supplier
        supplier = db.query(Supplier).first()
        if not supplier:
            print("No supplier found. Creating one...")
            supplier = Supplier(name="Test Fix Supplier", ledger_balance=0.0)
            db.add(supplier)
            db.commit()
            db.refresh(supplier)
            
        initial_bal = Decimal(str(supplier.ledger_balance or 0.0))
        print(f"Initial Supplier Balance: {initial_bal}")
        
        # 2. Simulate "Cash" GRN
        grn_no = f"TEST-FIX-{date.today().isoformat()}-2"
        grn = GRN(
            custom_grn_no=grn_no,
            supplier_id=supplier.id,
            payment_mode="Cash ", # Added trailing space to test strip()
            invoice_date=date.today(),
            net_total=500.0,
            status="Completed"
        )
        # Manually set dynamic properties used by AccountingService
        grn.grn_number = grn_no
        grn.total_amount = Decimal('500.00')
        grn.received_date = date.today()
        
        db.add(grn)
        db.commit()
        db.refresh(grn)
        
        print(f"Recorded GRN: {grn_no} with Mode='{grn.payment_mode}'")
        
        # 3. Call Accounting Service
        print("Calling AccountingService.record_purchase_transaction...")
        AccountingService.record_purchase_transaction(db, grn, user_id=None)
        
        # 4. Verify Results
        db.refresh(supplier)
        after_bal = Decimal(str(supplier.ledger_balance or 0.0))
        print(f"Supplier Balance After: {after_bal}")
        
        # Look for ledger entries
        res = db.execute(text("""
            SELECT transaction_type, debit_amount, credit_amount, balance 
            FROM supplier_ledger 
            WHERE reference_number = :ref
            ORDER BY id ASC
        """), {"ref": grn_no}).all()
        
        print("\nLedger Entries for this GRN:")
        for r in res:
            print(f"  Type: {r[0]}, Debit: {r[1]}, Credit: {r[2]}, Snapshot Balance: {r[3]}")
            
        if len(res) == 2:
            print("\n[SUCCESS] Exactly two entries created (Purchase & Payment).")
        else:
            print(f"\n[FAILURE] Expected 2 entries, found {len(res)}.")
            
        if abs(after_bal - initial_bal) < Decimal('0.01'):
            print("[SUCCESS] Supplier balance returned to initial state (as expected for Cash).")
        else:
            print(f"[FAILURE] Supplier balance mismatch: {initial_bal} -> {after_bal}")

    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_fix()
