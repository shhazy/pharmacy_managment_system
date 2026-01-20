from sqlalchemy import text
from app.database import engine

def debug_data():
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO tenant_t1, public"))
        
        # 1. Check GRN payment modes
        grn_sql = text("""
            SELECT custom_grn_no, payment_mode, net_total 
            FROM grns 
            WHERE custom_grn_no IN ('GRN-260119145843', 'GRN-260119174534')
        """)
        grns = conn.execute(grn_sql).all()
        print("\n--- GRN Data ---")
        for g in grns:
            print(dict(g._mapping))
            
        # 2. Check Supplier Ledger entries
        ledger_sql = text("""
            SELECT transaction_type, debit_amount, credit_amount, reference_number, description
            FROM supplier_ledger 
            WHERE reference_number IN ('GRN-260119145843', 'GRN-260119174534')
            ORDER BY transaction_date, id
        """)
        ledger = conn.execute(ledger_sql).all()
        print("\n--- Ledger Entries ---")
        for l in ledger:
            print(dict(l._mapping))

if __name__ == "__main__":
    debug_data()
