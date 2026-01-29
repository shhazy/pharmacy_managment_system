import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models.public_models import Tenant

PERMISSIONS_MATRIX = {
    "POS": ["view", "create", "edit", "delete"],
    "Products": ["view", "create", "edit", "delete"],
    "Inventory": ["view", "create", "edit", "delete"],
    "PurchaseOrder": ["view", "create", "edit", "delete"],
    "GRN": ["view", "create", "edit", "delete"],
    "Suppliers": ["view", "create", "edit", "delete"],
    "Patients": ["view", "create", "edit", "delete"],
    "Reports": ["view"],
    "Accounting": ["view", "create", "edit", "delete"],
    "Settings": ["view", "edit"],
    "Staff": ["view", "create", "edit", "delete"],
    "Roles": ["view", "create", "edit", "delete"],
}

def add_columns_if_not_exist(db, schema):
    # Check if column exists using information_schema
    result = db.execute(text(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = '{schema}' 
          AND table_name = 'permissions' 
          AND column_name = 'module'
    """)).fetchone()
    
    if not result:
        print(f"Column 'module' does not exist in {schema}. Adding columns...")
        try:
            db.execute(text("ALTER TABLE permissions ADD COLUMN module VARCHAR"))
            db.execute(text("ALTER TABLE permissions ADD COLUMN action VARCHAR"))
            db.commit()
            print("Columns added.")
        except Exception as e:
            print(f"Error adding columns: {e}")
            db.rollback()
    else:
        print(f"Column 'module' already exists in {schema}.")

def seed_permissions(db):
    print("Seeding permissions...")
    existing = db.execute(text("SELECT name FROM permissions")).fetchall()
    existing_names = {row[0] for row in existing}

    for module, actions in PERMISSIONS_MATRIX.items():
        for action in actions:
            perm_name = f"{module}:{action}"
            if perm_name not in existing_names:
                print(f"Adding permission: {perm_name}")
                db.execute(text(
                    "INSERT INTO permissions (name, module, action, description) VALUES (:name, :module, :action, :desc)"
                ), {
                    "name": perm_name,
                    "module": module,
                    "action": action,
                    "desc": f"Can {action} {module}"
                })
            else:
                # Update existing if module/action is null (migration)
                db.execute(text(
                    "UPDATE permissions SET module = :module, action = :action WHERE name = :name AND module IS NULL"
                ), {
                    "name": perm_name,
                    "module": module,
                    "action": action
                })
    
    db.commit()
    print("Permissions seeded.")

def main():
    db = SessionLocal()
    try:
        # 1. Get all tenants
        tenants = db.query(Tenant).all()
        schemas = ["public"] + [t.schema_name for t in tenants]
        
        print(f"Found schemas: {schemas}")

        for schema in schemas:
            print(f"--- Processing Schema: {schema} ---")
            try:
                db.execute(text(f"SET search_path TO {schema}"))
                add_columns_if_not_exist(db, schema)
                seed_permissions(db)
            except Exception as e:
                print(f"Error processing schema {schema}: {e}")
                db.rollback()

    finally:
        db.close()

if __name__ == "__main__":
    main()
