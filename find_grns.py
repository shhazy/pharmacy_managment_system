from sqlalchemy import text, inspect
from app.database import engine

def find_grns():
    inspector = inspect(engine)
    schemas = inspector.get_schema_names()
    
    target_grns = ['GRN-260119145843', 'GRN-260119174534']
    
    with engine.connect() as conn:
        for schema in schemas:
            if schema.startswith('tenant_'):
                print(f"\nChecking schema: {schema}")
                conn.execute(text(f"SET search_path TO {schema}, public"))
                
                # Check GRNs
                try:
                    res = conn.execute(text("SELECT custom_grn_no, payment_mode, net_total FROM grns")).all()
                    for r in res:
                        if r[0] in target_grns:
                            print(f"  [FOUND GRN] {r[0]}: Mode={r[1]}, Total={r[2]}")
                except Exception:
                    pass
                
                # Check Ledger
                try:
                    res = conn.execute(text("SELECT transaction_type, debit_amount, credit_amount, reference_number FROM supplier_ledger")).all()
                    for r in res:
                        if r[3] in target_grns:
                            print(f"  [FOUND LEDGER] {r[3]}: Type={r[0]}, Debit={r[1]}, Credit={r[2]}")
                except Exception:
                    pass

if __name__ == "__main__":
    find_grns()
