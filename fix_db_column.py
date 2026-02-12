import psycopg2

def add_column():
    try:
        conn = psycopg2.connect(
            dbname="pharmacy_db",
            user="postgres",
            password="1234",
            host="127.0.0.1",
            port="5432"
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if column exists
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='cash_register_sessions' AND column_name='closing_withdrawn'")
        result = cur.fetchone()
        
        if not result:
            print("Adding closing_withdrawn column...")
            cur.execute("ALTER TABLE cash_register_sessions ADD COLUMN closing_withdrawn NUMERIC(15, 2) DEFAULT 0")
            print("Column added successfully.")
        else:
            print("Column already exists.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_column()
