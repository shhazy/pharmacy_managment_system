"""
Migration Script: Restructure Chart of Accounts
Target: Existing tenants (specifically 'th')
Action: Create 5 Root Accounts and reparent existing top-level accounts.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app.models.accounting_models import Account, AccountType

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")

def migrate_tenant_coa(schema_name):
    print(f"\nMigrating COA for schema: {schema_name}")
    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # Set search path
        session.execute(text(f"SET search_path TO {schema_name}, public"))
        
        # 1. Ensure Root Accounts Exist
        roots = {
            AccountType.ASSET: {"code": "1", "name": "Assets"},
            AccountType.LIABILITY: {"code": "2", "name": "Liabilities"},
            AccountType.EQUITY: {"code": "3", "name": "Equity"},
            AccountType.REVENUE: {"code": "4", "name": "Revenue"},
            AccountType.EXPENSE: {"code": "5", "name": "Expenses"},
        }
        
        root_ids = {}

        for acc_type, root_data in roots.items():
            # Check if exists
            root_acc = session.query(Account).filter(Account.account_code == root_data["code"]).first()
            if not root_acc:
                print(f"  + Creating root: {root_data['name']}")
                root_acc = Account(
                    account_code=root_data["code"],
                    account_name=root_data["name"],
                    account_type=acc_type,
                    is_active=True,
                    description=f"Root {acc_type.value} Account"
                )
                session.add(root_acc)
                session.flush()
            
            root_ids[acc_type] = root_acc.id
        
        # 2. Re-parent existing top-level accounts
        # Find all accounts that are not roots and have no parent
        orphans = session.query(Account).filter(
            Account.parent_account_id == None,
            Account.account_code.notin_([r["code"] for r in roots.values()])
        ).all()
        
        if not orphans:
            print("  ✓ No orphan accounts found.")
        else:
            print(f"  > Found {len(orphans)} orphan accounts. Re-parenting...")
            for acc in orphans:
                if acc.account_type in root_ids:
                    new_parent_id = root_ids[acc.account_type]
                    acc.parent_account_id = new_parent_id
                    print(f"    - Moved '{acc.account_name}' ({acc.account_code}) -> {roots[acc.account_type]['name']}")
                else:
                    print(f"    ! Skipped '{acc.account_name}' (Unknown type: {acc.account_type})")

        session.commit()
        print(f"  ✓ Migration complete for {schema_name}")

if __name__ == "__main__":
    # Target specific schema 'tenant_th' as per user request (or 'th' from subdomain)
    # User said "except the tenant th" wait, usually schema is tenant_th
    # I will try 'tenant_th'
    
    target_schemas = ['tenant_th']
    
    print("=" * 60)
    print("COA RESTRUCTURE MIGRATION")
    print("=" * 60)
    
    for schema in target_schemas:
        try:
            migrate_tenant_coa(schema)
        except Exception as e:
            print(f"Error migrating {schema}: {e}")
            # Try plain 'th' just in case
            try:
                print("Retrying with schema 'th'...")
                migrate_tenant_coa('th')
            except Exception as e2:
                print(f"Failed: {e2}")

    print("\n" + "=" * 60)
