from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models import GRN, Supplier
from app.models.accounting_models import SupplierLedger

def debug_grns():
    db = SessionLocal()
    try:
        # Get all schemas
        result = db.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'"))
        schemas = [row[0] for row in result]
        
        for schema in schemas:
            print(f"\n--- Checking Schema: {schema} ---")
            db.execute(text(f"SET search_path TO {schema}, public"))
            
            # Find recent Cash GRNs
            grns = db.query(GRN).filter(GRN.payment_mode.ilike('%cash%')).order_by(GRN.id.desc()).limit(10).all()
            
            if not grns:
                print("  No Cash GRNs found.")
                continue
                
            for grn in grns:
                print(f"  [GRN] ID: {grn.id}, No: {grn.custom_grn_no}, Mode: '{grn.payment_mode}', Total: {grn.net_total}")
                
                # Check Ledger Entries directly with SQL to avoid Enum issues
                ledger_entries = db.execute(text("""
                    SELECT transaction_type, debit_amount, credit_amount, balance, id
                    FROM supplier_ledger 
                    WHERE reference_number = :ref
                    ORDER BY id ASC
                """), {"ref": grn.custom_grn_no}).all()
                
                if not ledger_entries:
                    print("    No ledger entries found.")
                else:
                    for entry in ledger_entries:
                        # entry[0] is the enum/string
                        print(f"    [LEDGER] ID: {entry[4]}, Type: {entry[0]}, Dr: {entry[1]}, Cr: {entry[2]}, Bal: {entry[3]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_grns()
