
import psycopg2
from datetime import datetime

def fix_product_flags():
    db_config = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
    conn = psycopg2.connect(db_config)
    cur = conn.cursor()
    
    tenant_schema = "tenant_tk"
    print(f"Fixing product flags for schema: {tenant_schema}")
    
    try:
        cur.execute(f"SET search_path TO {tenant_schema}, public")
        
        # Update products with NULL flags to defaults
        cur.execute("""
            UPDATE products 
            SET 
                control_drug = COALESCE(control_drug, False),
                product_type = COALESCE(product_type, 1),
                allow_below_cost_sale = COALESCE(allow_below_cost_sale, False),
                allow_price_change = COALESCE(allow_price_change, True),
                active = COALESCE(active, True)
            WHERE 
                control_drug IS NULL OR 
                product_type IS NULL OR 
                allow_below_cost_sale IS NULL OR 
                allow_price_change IS NULL OR
                active IS NULL
        """)
        
        print(f"Updated {cur.rowcount} products with missing flag defaults.")
        
        conn.commit()
    except Exception as e:
        print(f"Error fixing product flags: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    fix_product_flags()
