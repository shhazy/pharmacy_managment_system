
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def fix_store_ids():
    conn = psycopg2.connect("postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
    cur = conn.cursor()
    
    db_name = "tenant_tk"
    print(f"Fixing store_id values for {db_name}...")
    
    try:
        cur.execute(f"SET search_path TO {db_name}, public")
        
        # 1. Ensure store with ID 1 exists (it should, but safety first)
        cur.execute("SELECT id FROM stores WHERE id = 1")
        if not cur.fetchone():
            print("Creating default store (ID: 1)...")
            cur.execute("INSERT INTO stores (id, name, address) VALUES (1, 'Main Branch', 'Default Address') ON CONFLICT (id) DO NOTHING")
        
        # 2. Update registers with NULL store_id
        cur.execute("UPDATE cash_registers SET store_id = 1 WHERE store_id IS NULL")
        print(f"Updated {cur.rowcount} registers.")
        
        # 3. Update users with NULL store_id
        cur.execute("UPDATE users SET store_id = 1 WHERE store_id IS NULL")
        print(f"Updated {cur.rowcount} users.")
        
        conn.commit()
        print("Changes committed successfully.")
        
    except Exception as e:
        print(f"Error during fix: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    fix_store_ids()
