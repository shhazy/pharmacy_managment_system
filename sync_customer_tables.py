from app.database import engine, Base
from app.models import Tenant
from app.models.customer_models import Customer, CustomerType, CustomerGroup
from sqlalchemy import text
from app.database import SessionLocal

def sync_schemas():
    db = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        for t in tenants:
            print(f"Syncing schema for {t.subdomain} ({t.schema_name})...")
            with engine.connect() as conn:
                conn.execute(text(f"SET search_path TO {t.schema_name}"))
                Base.metadata.create_all(bind=conn, tables=[
                    CustomerGroup.__table__, 
                    CustomerType.__table__, 
                    Customer.__table__
                ])
                conn.commit()
        print("Successfully synced all tenant schemas.")
    except Exception as e:
        print(f"Error syncing schemas: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sync_schemas()
