from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.accounting_models import Account, AccountType

def seed_standard_coa():
    db = SessionLocal()
    try:
        # Get all schemas
        result = db.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'tenant_%'"))
        schemas = [row[0] for row in result]
        
        standard_accounts = [
            {"code": "1000", "name": "Cash In Hand", "account_type": AccountType.ASSET},
            {"code": "1300", "name": "Inventory", "account_type": AccountType.ASSET},
            {"code": "2000", "name": "Accounts Payable", "account_type": AccountType.LIABILITY},
            {"code": "4000", "name": "Sales Revenue", "account_type": AccountType.REVENUE},
            {"code": "5000", "name": "Cost of Goods Sold", "account_type": AccountType.EXPENSE},
            {"code": "1200", "name": "Accounts Receivable", "account_type": AccountType.ASSET},
            {"code": "5400", "name": "Discount Allowed", "account_type": AccountType.EXPENSE},
        ]
        
        for schema in schemas:
            print(f"\n--- Seeding Schema: {schema} ---")
            db.execute(text(f"SET search_path TO {schema}, public"))
            
            for acc in standard_accounts:
                # Check if account exists - USE CORRECT COLUMN NAME 'account_code'
                existing = db.execute(text("SELECT id FROM accounts WHERE account_code = :code"), {"code": acc["code"]}).first()
                if not existing:
                    print(f"  [MISSING] Seeding {acc['code']} - {acc['name']}...")
                    db.execute(text("""
                        INSERT INTO accounts (account_code, account_name, account_type, is_active, ledger_balance, current_balance)
                        VALUES (:code, :name, :type, true, 0.0, 0.0)
                    """), {
                        "code": acc["code"],
                        "name": acc["name"],
                        "type": acc["account_type"].value
                    })
                else:
                    print(f"  [OK] {acc['code']} exists.")
            
            db.commit()
            print(f"✓ All standard accounts verified for {schema}")

    except Exception as e:
        print(f"Error seeding COA: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_standard_coa()
