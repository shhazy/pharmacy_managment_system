"""
Accounting Module Database Migration & Seed Script
Creates accounting tables and seeds default Chart of Accounts
"""

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, get_db
from app.models.accounting_models import Account, AccountType
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db")

def create_accounting_tables():
    """Create all accounting tables"""
    engine = create_engine(DATABASE_URL)
    
    # Get all schemas
    schemas = inspect(engine).get_schema_names()
    
    print("Creating accounting tables in all tenant schemas...")
    
    for schema in schemas:
        if schema in ['information_schema', 'pg_catalog', 'pg_toast', 'public']:
            continue
        
        print(f"\nProcessing schema: {schema}")
        
        try:
            with engine.connect() as conn:
                # Set search path
                conn.execute(text(f"SET search_path TO {schema}, public"))
                conn.commit()
                
                # Create tables
                Base.metadata.create_all(bind=engine, checkfirst=True)
                
                print(f"  ✓ Tables created in {schema}")
                
        except Exception as e:
            print(f"  ✗ Error in {schema}: {e}")
    
    print("\n✓ Accounting tables created successfully!")

def seed_chart_of_accounts():
    """Seed default Chart of Accounts"""
    engine = create_engine(DATABASE_URL)
    schemas = inspect(engine).get_schema_names()
    
    # Default Chart of Accounts
    default_accounts = [
        # ROOTS
        {"code": "1", "name": "Assets", "type": AccountType.ASSET, "parent": None},
        {"code": "2", "name": "Liabilities", "type": AccountType.LIABILITY, "parent": None},
        {"code": "3", "name": "Equity", "type": AccountType.EQUITY, "parent": None},
        {"code": "4", "name": "Revenue", "type": AccountType.REVENUE, "parent": None},
        {"code": "5", "name": "Expenses", "type": AccountType.EXPENSE, "parent": None},

        # ASSETS (Children of 1)
        {"code": "1000", "name": "Cash", "type": AccountType.ASSET, "parent": "1"},
        {"code": "1100", "name": "Bank Account", "type": AccountType.ASSET, "parent": "1"},
        {"code": "1200", "name": "Accounts Receivable", "type": AccountType.ASSET, "parent": "1"},
        {"code": "1300", "name": "Inventory", "type": AccountType.ASSET, "parent": "1"},
        {"code": "1400", "name": "Prepaid Expenses", "type": AccountType.ASSET, "parent": "1"},
        {"code": "1500", "name": "Fixed Assets", "type": AccountType.ASSET, "parent": "1"},
        {"code": "1510", "name": "Furniture & Fixtures", "type": AccountType.ASSET, "parent": "1500"},
        {"code": "1520", "name": "Equipment", "type": AccountType.ASSET, "parent": "1500"},
        
        # LIABILITIES (Children of 2)
        {"code": "2000", "name": "Accounts Payable", "type": AccountType.LIABILITY, "parent": "2"},
        {"code": "2100", "name": "Salaries Payable", "type": AccountType.LIABILITY, "parent": "2"},
        {"code": "2200", "name": "Tax Payable", "type": AccountType.LIABILITY, "parent": "2"},
        {"code": "2300", "name": "Short-term Loans", "type": AccountType.LIABILITY, "parent": "2"},
        
        # EQUITY (Children of 3)
        {"code": "3000", "name": "Owner's Capital", "type": AccountType.EQUITY, "parent": "3"},
        {"code": "3100", "name": "Retained Earnings", "type": AccountType.EQUITY, "parent": "3"},
        {"code": "3200", "name": "Drawings", "type": AccountType.EQUITY, "parent": "3"},
        
        # REVENUE (Children of 4)
        {"code": "4000", "name": "Sales Revenue", "type": AccountType.REVENUE, "parent": "4"},
        {"code": "4100", "name": "Other Income", "type": AccountType.REVENUE, "parent": "4"},
        
        # EXPENSES (Children of 5)
        {"code": "5000", "name": "Cost of Goods Sold", "type": AccountType.EXPENSE, "parent": None},
        {"code": "5100", "name": "Salaries Expense", "type": AccountType.EXPENSE, "parent": "5"},
        {"code": "5200", "name": "Rent Expense", "type": AccountType.EXPENSE, "parent": "5"},
        {"code": "5300", "name": "Utilities Expense", "type": AccountType.EXPENSE, "parent": "5"},
        {"code": "5400", "name": "Discount Given", "type": AccountType.EXPENSE, "parent": "5"},
        {"code": "5500", "name": "Other Expenses", "type": AccountType.EXPENSE, "parent": "5"},
        {"code": "5600", "name": "Depreciation Expense", "type": AccountType.EXPENSE, "parent": "5"},
    ]
    
    print("\nSeeding Chart of Accounts...")
    
    for schema in schemas:
        if schema in ['information_schema', 'pg_catalog', 'pg_toast', 'public']:
            continue
        
        print(f"\nSeeding accounts in schema: {schema}")
        
        try:
            with engine.connect() as conn:
                # Set search path
                conn.execute(text(f"SET search_path TO {schema}, public"))
                conn.commit()
            
            # Create session with schema context
            with Session(engine) as session:
                session.execute(text(f"SET search_path TO {schema}, public"))
                
                # Check if accounts already exist
                existing_count = session.query(Account).count()
                if existing_count > 0:
                    print(f"  ⚠ Accounts already exist ({existing_count} accounts). Skipping...")
                    continue
                
                # Create account code to ID mapping for parent relationships
                account_map = {}
                
                # First pass: Create all accounts without parent relationships
                for acc_data in default_accounts:
                    account = Account(
                        account_code=acc_data["code"],
                        account_name=acc_data["name"],
                        account_type=acc_data["type"],
                        is_active=True,
                        opening_balance=0.0,
                        current_balance=0.0,
                        description=f"Default {acc_data['type'].value} account"
                    )
                    session.add(account)
                    session.flush()  # Get the ID
                    account_map[acc_data["code"]] = account.id
                
                # Second pass: Update parent relationships
                for acc_data in default_accounts:
                    if acc_data["parent"]:
                        account = session.query(Account).filter(
                            Account.account_code == acc_data["code"]
                        ).first()
                        if account:
                            account.parent_account_id = account_map.get(acc_data["parent"])
                
                session.commit()
                print(f"  ✓ Seeded {len(default_accounts)} accounts in {schema}")
                
        except Exception as e:
            print(f"  ✗ Error in {schema}: {e}")
    
    print("\n✓ Chart of Accounts seeded successfully!")

if __name__ == "__main__":
    print("=" * 60)
    print("ACCOUNTING MODULE SETUP")
    print("=" * 60)
    
    # Step 1: Create tables
    create_accounting_tables()
    
    # Step 2: Seed Chart of Accounts
    seed_chart_of_accounts()
    
    print("\n" + "=" * 60)
    print("✓ ACCOUNTING MODULE SETUP COMPLETE!")
    print("=" * 60)
