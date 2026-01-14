from app.database import SessionLocal, engine
from sqlalchemy import text
from app.models.procurement_models import GRN, GRNItem

def fix_tenant_schema(tenant_id):
    db = SessionLocal()
    try:
        print(f"--- Fixing Schema for Tenant: {tenant_id} ---")
        
        schema = f"tenant_{tenant_id}"
        db.execute(text(f"SET search_path TO {schema}, public"))
        
        # Create Tables using SQLAlchemy metadata
        # We need to bind the engine to the schema? 
        # Or just use the session's connection which has the search path set?
        # metadata.create_all(engine) usually creates in default schema unless specified.
        # But if we use the engine, it might not respect the session's search path.
        
        # Method: Use Table.create(bind=connection)
        
        connection = db.connection()
        print("Creating GRN table...")
        GRN.__table__.create(bind=connection, checkfirst=True)
        
        print("Creating GRNItem table...")
        GRNItem.__table__.create(bind=connection, checkfirst=True)
        
        db.commit()
        print(" Tables created successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix_tenant_schema("t7")
