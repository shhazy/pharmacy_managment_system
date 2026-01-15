from app.database import engine
from sqlalchemy import inspect, text

def check():
    inspector = inspect(engine)
    print("Tables:", inspector.get_table_names())
    
    for table in ['purchase_order_items', 'products']:
        if table in inspector.get_table_names():
            cols = [c['name'] for c in inspector.get_columns(table)]
            print(f"Columns in {table}:", cols)
        else:
            print(f"Table {table} not found!")

if __name__ == "__main__":
    check()
