from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

# Import models to ensure they are registered
from app.models.accounting_models import Account, AccountType

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")
engine = create_engine(DATABASE_URL)

def migrate_accounts():
    with engine.connect() as conn:
        # Get all tenant schemas
        result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%';"))
        schemas = [row[0] for row in result]
        
        for schema in schemas:
            print(f"Migrating accounts for schema: {schema}")
            try:
                # Set search path for this tenant
                conn.execute(text(f"SET search_path TO {schema}"))
                
                # Check if Advance Tax Receivable already exists
                check_result = conn.execute(text("SELECT id FROM accounts WHERE account_code = '1450'")).fetchone()
                
                if not check_result:
                    print(f"Adding Advance Tax Receivable (1450) to {schema}")
                    # Get parent ID (Assets root '1')
                    parent_result = conn.execute(text("SELECT id FROM accounts WHERE account_code = '1'")).fetchone()
                    parent_id = parent_result[0] if parent_result else None
                    
                    conn.execute(text("""
                        INSERT INTO accounts (account_code, account_name, account_type, parent_account_id, is_active, opening_balance, current_balance, description, created_at, updated_at)
                        VALUES (:code, :name, :type, :parent_id, :is_active, :op_bal, :curr_bal, :desc, :created_at, :updated_at)
                    """), {
                        "code": "1450",
                        "name": "Advance Tax Receivable",
                        "type": "ASSET",
                        "parent_id": parent_id,
                        "is_active": True,
                        "op_bal": 0.0,
                        "curr_bal": 0.0,
                        "desc": "Advance Tax paid on purchases",
                        "created_at": "now()",
                        "updated_at": "now()"
                    })
                    conn.commit()
                    print(f"✓ Added 1450 to {schema}")
                else:
                    print(f"✓ Account 1450 already exists in {schema}")
            except Exception as e:
                print(f"Error migrating {schema}: {e}")
                conn.rollback()

if __name__ == "__main__":
    migrate_accounts()
