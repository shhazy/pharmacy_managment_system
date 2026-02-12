import psycopg2

def list_schemas():
    try:
        conn = psycopg2.connect(
            dbname="pharmacy_db",
            user="postgres",
            password="1234",
            host="127.0.0.1",
            port="5432"
        )
        cur = conn.cursor()
        
        cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')")
        schemas = cur.fetchall()
        
        print("Found schemas:", [s[0] for s in schemas])
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_schemas()
