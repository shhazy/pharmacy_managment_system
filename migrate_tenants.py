from sqlalchemy import create_engine, text
from app.database import engine, Base
from app.models import Tenant
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_all_tenants():
    # 1. Get all tenants
    with Session(engine) as session:
        tenants = session.query(Tenant).all()
        schemas = ["public"] + [t.schema_name for t in tenants]
    
    print(f"Starting migration for {len(schemas)} schemas...")

    for schema in schemas:
        print(f"Migrating schema: {schema}")
        try:
            # Set search path for this schema
            with engine.connect() as conn:
                conn.execute(text(f"SET search_path TO {schema}"))
                # Create all tables defined in models for this schema
                Base.metadata.create_all(bind=conn)
                conn.commit()
            print(f"  Successfully migrated {schema}")
        except Exception as e:
            print(f"  Failed to migrate {schema}: {e}")

if __name__ == "__main__":
    migrate_all_tenants()
