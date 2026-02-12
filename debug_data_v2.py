
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_data():
    conn = psycopg2.connect("postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
    cur = conn.cursor()
    
    db_name = "tenant_tk"
    print(f"Checking data for {db_name}...")
    
    # Check registers
    cur.execute(f"SET search_path TO {db_name}, public")
    cur.execute("SELECT id, register_name, store_id FROM cash_registers")
    registers = cur.fetchall()
    print("Registers:")
    for r in registers:
        print(f"  ID: {r[0]}, Name: {r[1]}, Store ID: {r[2]}")
        
    # Check users
    cur.execute("SELECT id, username, store_id FROM users")
    users = cur.fetchall()
    print("Users:")
    for u in users:
        print(f"  ID: {u[0]}, Username: {u[1]}, Store ID: {u[2]}")
        
    # Check stores
    cur.execute("SELECT id, name FROM stores")
    stores = cur.fetchall()
    print("Stores:")
    for s in stores:
        print(f"  ID: {s[0]}, Name: {s[1]}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_data()
