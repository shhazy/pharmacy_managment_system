import psycopg2

def fix_all_tenants():
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
        
        # Get all schemas
        cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%' OR schema_name = 'public'")
        schemas = [s[0] for s in cur.fetchall()]
        
        print(f"Found {len(schemas)} schemas to check: {schemas}")
        
        for schema in schemas:
            print(f"Checking schema: {schema}")
            # Check if table exists in schema
            cur.execute(f"SELECT 1 FROM information_schema.tables WHERE table_schema = '{schema}' AND table_name = 'cash_register_sessions'")
            if not cur.fetchone():
                print(f"  Table cash_register_sessions not found in {schema}, skipping.")
                continue
                
            # Check if column exists
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_schema='{schema}' AND table_name='cash_register_sessions' AND column_name='closing_withdrawn'")
            if not cur.fetchone():
                print(f"  Adding closing_withdrawn column to {schema}.cash_register_sessions...")
                try:
                    cur.execute(f"ALTER TABLE {schema}.cash_register_sessions ADD COLUMN closing_withdrawn NUMERIC(15, 2) DEFAULT 0")
                    print("  Success.")
                except Exception as e:
                    print(f"  Failed: {e}")
            else:
                print(f"  Column already exists in {schema}.")
            
        cur.close()
        conn.close()
        print("All schemas processed.")
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    fix_all_tenants()
