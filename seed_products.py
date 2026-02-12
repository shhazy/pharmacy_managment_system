
import psycopg2
from datetime import datetime, timedelta
import random

def seed_products():
    db_config = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
    conn = psycopg2.connect(db_config)
    cur = conn.cursor()
    
    tenant_schema = "tenant_tk"
    print(f"Seeding products for schema: {tenant_schema}")
    
    try:
        cur.execute(f"SET search_path TO {tenant_schema}, public")
        
        # 1. Add some more generics if they don't exist
        generics = [
            "Amoxicillin", "Metronidazole", "Ibuprofen", "Clarithromycin", 
            "Loratadine", "Omeprazole", "Aspirin", "Alginic Acid", "Mefenamic Acid"
        ]
        
        for g in generics:
            cur.execute("SELECT id FROM generics WHERE name = %s", (g,))
            if not cur.fetchone():
                cur.execute("INSERT INTO generics (name, created_at, updated_at, is_active) VALUES (%s, %s, %s, %s)", 
                           (g, datetime.utcnow(), datetime.utcnow(), True))
        
        # Get mapping of generic names to IDs
        cur.execute("SELECT id, name FROM generics")
        generic_map = {name: id for id, name in cur.fetchall()}
        
        # Get mapping of categories
        cur.execute("SELECT id, name FROM categories")
        category_map = {name: id for id, name in cur.fetchall()}
        
        # Get manufacturers
        cur.execute("SELECT id FROM manufacturers LIMIT 3")
        mfg_ids = [row[0] for row in cur.fetchall()]
        
        products_data = [
            ("Panadol 500mg", "Analgesics", "Paracetamol"),
            ("Amoxil 250mg", "Antibiotics", "Amoxicillin"),
            ("Flagyl 400mg", "Antibiotics", "Metronidazole"),
            ("Brufen 400mg", "Analgesics", "Ibuprofen"),
            ("Augmentin 625mg", "Antibiotics", "Amoxicillin"),
            ("Arinac Forte", "Analgesics", "Ibuprofen"),
            ("Disprin", "Analgesics", "Aspirin"),
            ("Gaviscon Syrup", "Analgesics", "Alginic Acid"),
            ("Hydryllin Syrup", "Analgesics", "Paracetamol"),
            ("Ponstan Forte", "Analgesics", "Mefenamic Acid"),
            ("Zyrtec 10mg", "Analgesics", "Loratadine"),
            ("Entamizole", "Antibiotics", "Metronidazole"),
            ("Surbex-Z", "Supplements", "Paracetamol"),
            ("CaC 1000 Plus", "Supplements", "Paracetamol"),
            ("Polyfax Ointment", "Antibiotics", "Amoxicillin"),
            ("Voltral Emulgel", "Analgesics", "Ibuprofen"),
            ("Calpol 250mg", "Analgesics", "Paracetamol"),
            ("Softin 10mg", "Analgesics", "Loratadine"),
            ("Klaricid 250mg", "Antibiotics", "Clarithromycin"),
            ("Risek 40mg", "Analgesics", "Omeprazole"),
        ]
        
        print(f"Inserting {len(products_data)} products...")
        
        for p_name, cat_name, gen_name in products_data:
            cat_id = category_map.get(cat_name, category_map.get('Analgesics', 1))
            gen_id = generic_map.get(gen_name, 1)
            mfg_id = random.choice(mfg_ids) if mfg_ids else 1
            
            # Check if product exists
            cur.execute("SELECT id FROM products WHERE product_name = %s", (p_name,))
            existing_p = cur.fetchone()
            
            if existing_p:
                p_id = existing_p[0]
                print(f"Product '{p_name}' already exists. Skipping insertion.")
            else:
                # Insert product
                cur.execute("""
                    INSERT INTO products 
                    (product_name, line_item_id, category_id, generics_id, manufacturer_id, active, date, 
                     base_unit_id, preferred_pos_unit_id, control_drug, product_type, allow_below_cost_sale, allow_price_change) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (p_name, 1, cat_id, gen_id, mfg_id, True, datetime.utcnow(), 3, 3, False, 1, False, True))
                p_id = cur.fetchone()[0]
            
            # Add stock inventory for this product
            batch_no = f"BATCH-{random.randint(1000, 9999)}"
            expiry = datetime.utcnow() + timedelta(days=random.randint(365, 730))
            qty = random.randint(50, 500)
            cost = round(random.uniform(10.0, 100.0), 2)
            price = round(cost * 1.25, 2)
            
            cur.execute("""
                INSERT INTO stock_inventory 
                (product_id, batch_number, expiry_date, quantity, unit_cost, selling_price, retail_price, store_id, is_available, created_at, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (p_id, batch_no, expiry, qty, cost, price, price, 1, True, datetime.utcnow(), datetime.utcnow()))
            
        conn.commit()
        print("Successfully seeded 20 products and stock.")
        
    except Exception as e:
        print(f"Error seeding products: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed_products()
