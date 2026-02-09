import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import DATABASE_URL, SessionLocal
from app.models.public_models import Tenant

def patch_database():
    db = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        schemas = ["public"] + [t.schema_name for t in tenants]
        
        for schema in schemas:
            print(f"Patching schema: {schema}")
            db.execute(text(f"SET search_path TO {schema}"))
            
            # Add columns to app_settings
            try:
                db.execute(text("ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS invoice_template_id VARCHAR DEFAULT 'default'"))
                db.execute(text("ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS invoice_custom_config JSONB"))
                print(f"  - Updated app_settings in {schema}")
            except Exception as e:
                print(f"  - Skip/Error on app_settings in {schema}: {e}")
                db.rollback()
            
            db.commit()
        print("Done!")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    patch_database()
