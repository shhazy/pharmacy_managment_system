import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models import Tenant, Base

def ensure_app_settings():
    db = SessionLocal()
    try:
        # 1. Get all tenants
        tenants = db.query(Tenant).all()
        schemas = [t.schema_name for t in tenants] + ['public']
        
        for schema in schemas:
            print(f"Ensuring 'app_settings' table in schema: {schema}")
            try:
                # Create the table if it doesn't exist
                # We use raw SQL because Base.metadata.create_all doesn't respect search_path easily in a loop without re-binding
                db.execute(text(f"SET search_path TO {schema}"))
                db.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS app_settings (
                        id SERIAL PRIMARY KEY,
                        default_listing_rows INTEGER DEFAULT 10,
                        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.commit()
                print(f"  - Table ensured.")
            except Exception as e:
                db.rollback()
                print(f"  - Error in schema {schema}: {str(e)}")
        
    finally:
        db.close()

if __name__ == "__main__":
    ensure_app_settings()
