from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def check_constraints():
    schema = "tenant_tk"
    with engine.connect() as conn:
        conn.execute(text(f"SET search_path TO {schema}, public"))
        
        query = """
        SELECT 
            tc.table_schema, 
            tc.table_name, 
            kcu.column_name, 
            ccu.table_schema AS foreign_table_schema, 
            ccu.table_name AS foreign_table_name 
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu 
          ON tc.constraint_name = kcu.constraint_name 
          AND tc.table_schema = kcu.table_schema 
        JOIN information_schema.constraint_column_usage AS ccu 
          ON ccu.constraint_name = tc.constraint_name 
          AND ccu.table_schema = tc.table_schema 
        WHERE tc.constraint_type = 'FOREIGN KEY' 
          AND tc.table_name='sale_return_items';
        """
        res = conn.execute(text(query)).fetchall()
        print("--- Constraints for sale_return_items ---")
        for row in res:
            print(f"Schema: {row[0]}, Table: {row[1]}, Column: {row[2]}, Foreign Schema: {row[3]}, Foreign Table: {row[4]}")

if __name__ == "__main__":
    check_constraints()
