"""
Migration script to add stock_inventory and update stock_adjustments tables
Run this script to add the new inventory tracking tables to your database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.database import DATABASE_URL, SessionLocal
from app.models import Base, StockInventory, StockAdjustment

def run_migration():
    """
    Create stock_inventory and stock_adjustments tables in all tenant schemas
    """
    engine = create_engine(DATABASE_URL)
    db = SessionLocal()
    
    try:
        print("🔄 Starting migration for stock_inventory and stock_adjustments tables...")
        
        # Get all tenant schemas
        result = db.execute(text("SELECT schema_name FROM public.tenants WHERE is_active = true"))
        tenants = result.fetchall()
        
        print(f"📋 Found {len(tenants)} active tenant(s)")
        
        for tenant in tenants:
            schema_name = tenant[0]
            print(f"\n🏢 Processing tenant schema: {schema_name}")
            
            # Set search path to tenant schema
            db.execute(text(f"SET search_path TO {schema_name}, public"))
            
            # Check if grns table exists
            grns_exists = db.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = '{schema_name}' 
                    AND table_name = 'grns'
                );
            """)).scalar()
            
            # Create stock_inventory table
            print(f"  ✅ Creating stock_inventory table in {schema_name}...")
            
            if grns_exists:
                # Create with GRN foreign key
                db.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {schema_name}.stock_inventory (
                        inventory_id SERIAL PRIMARY KEY,
                        product_id INTEGER NOT NULL REFERENCES {schema_name}.products(id),
                        batch_number VARCHAR(100),
                        expiry_date TIMESTAMP,
                        quantity DECIMAL(10,2) NOT NULL DEFAULT 0,
                        unit_cost DECIMAL(10,2),
                        selling_price DECIMAL(10,2),
                        warehouse_location VARCHAR(100),
                        store_id INTEGER REFERENCES {schema_name}.stores(id),
                        supplier_id INTEGER REFERENCES {schema_name}.suppliers(id),
                        grn_id INTEGER REFERENCES {schema_name}.grns(id),
                        is_available BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
            else:
                # Create without GRN foreign key (for tenants without procurement module)
                print(f"  ⚠️  GRNs table not found in {schema_name}, creating stock_inventory without GRN constraint")
                db.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {schema_name}.stock_inventory (
                        inventory_id SERIAL PRIMARY KEY,
                        product_id INTEGER NOT NULL REFERENCES {schema_name}.products(id),
                        batch_number VARCHAR(100),
                        expiry_date TIMESTAMP,
                        quantity DECIMAL(10,2) NOT NULL DEFAULT 0,
                        unit_cost DECIMAL(10,2),
                        selling_price DECIMAL(10,2),
                        warehouse_location VARCHAR(100),
                        store_id INTEGER REFERENCES {schema_name}.stores(id),
                        supplier_id INTEGER REFERENCES {schema_name}.suppliers(id),
                        grn_id INTEGER,
                        is_available BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))

            # FIX: Add store_id if it's missing from existing table
            db.execute(text(f"""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_schema='{schema_name}' AND table_name='stock_inventory' AND column_name='store_id') THEN
                        ALTER TABLE {schema_name}.stock_inventory ADD COLUMN store_id INTEGER REFERENCES {schema_name}.stores(id);
                    END IF;
                END $$;
            """))
            
            # Create index on batch_number for faster lookups
            db.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_stock_inventory_batch 
                ON {schema_name}.stock_inventory(batch_number);
            """))
            
            # Create index on grn_id for traceability
            db.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_stock_inventory_grn 
                ON {schema_name}.stock_inventory(grn_id);
            """))
            
            # Drop old stock_adjustments table if it exists (simple version)
            print(f"  🔄 Updating stock_adjustments table in {schema_name}...")
            db.execute(text(f"DROP TABLE IF EXISTS {schema_name}.stock_adjustments CASCADE"))
            
            # Create new comprehensive stock_adjustments table
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.stock_adjustments (
                    adjustment_id SERIAL PRIMARY KEY,
                    product_id INTEGER NOT NULL REFERENCES {schema_name}.products(id),
                    batch_number VARCHAR(100),
                    inventory_id INTEGER REFERENCES {schema_name}.stock_inventory(inventory_id),
                    adjustment_type VARCHAR(50) NOT NULL,
                    quantity_adjusted DECIMAL(10,2) NOT NULL,
                    previous_quantity DECIMAL(10,2),
                    new_quantity DECIMAL(10,2),
                    reason TEXT,
                    reference_number VARCHAR(100),
                    adjustment_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    adjusted_by INTEGER REFERENCES {schema_name}.users(id),
                    approved_by INTEGER REFERENCES {schema_name}.users(id),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create index on inventory_id
            db.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_stock_adjustments_inventory 
                ON {schema_name}.stock_adjustments(inventory_id);
            """))
            
            # Create index on adjustment_date for reporting
            db.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_stock_adjustments_date 
                ON {schema_name}.stock_adjustments(adjustment_date);
            """))
            
            db.commit()
            print(f"  ✅ Successfully migrated {schema_name}")
        
        print("\n✅ Migration completed successfully for all tenants!")
        print("\n📊 Summary:")
        print(f"   - Created stock_inventory table with GRN traceability")
        print(f"   - Updated stock_adjustments table with comprehensive audit trail")
        print(f"   - Added indexes for performance optimization")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 70)
    print("  STOCK INVENTORY & ADJUSTMENTS MIGRATION")
    print("=" * 70)
    run_migration()
