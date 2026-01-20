from sqlalchemy import text, inspect
from app.database import engine

def check_columns():
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO tenant_t1, public"))
        inspector = inspect(engine)
        
        tables = ['suppliers', 'supplier_ledger', 'customer_ledger', 'invoices', 'journal_entries', 'journal_entry_lines', 'patients']
        
        for table in tables:
            try:
                columns = inspector.get_columns(table, schema='tenant_t1')
                col_names = [c['name'] for c in columns]
                print(f"{table.upper()}: {col_names}")
            except Exception as e:
                print(f"Error checking {table}: {e}")

if __name__ == "__main__":
    check_columns()
