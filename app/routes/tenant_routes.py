from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from datetime import datetime, timedelta
import traceback

from ..database import engine, Base, get_db, SessionLocal
from ..models import (
    Tenant, User, Role, Product, SuperAdmin, Permission, 
    StockInventory, Category, Manufacturer, Supplier, Store
)
from ..schemas import TenantCreate, TenantResponse
from ..auth import get_password_hash, get_current_superadmin

router = APIRouter()

@router.post("/", response_model=TenantResponse)
def create_tenant(tenant_in: TenantCreate, db: Session = Depends(get_db), admin: SuperAdmin = Depends(get_current_superadmin)):
    try:
        schema_name = f"tenant_{tenant_in.subdomain}"
        
        # 1. Primary Identity Checks
        if db.query(Tenant).filter(Tenant.subdomain == tenant_in.subdomain).first():
            raise HTTPException(status_code=400, detail="Subdomain already exists")
        if db.query(Tenant).filter(Tenant.name == tenant_in.name).first():
            raise HTTPException(status_code=400, detail="Pharmacy name already exists")

        # 2. Infrastructure Setup (Schema)
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            conn.commit()
            
            # Set path for creation
            conn.execute(text(f"SET search_path TO {schema_name}"))
            tenant_tables = [t for t in Base.metadata.sorted_tables if t.schema != "public"]
            Base.metadata.create_all(bind=conn, tables=tenant_tables)
            conn.commit()
        
        # 3. Register Tenant in Global Registry
        db_tenant = Tenant(
            name=tenant_in.name, 
            subdomain=tenant_in.subdomain, 
            schema_name=schema_name, 
            admin_username=tenant_in.admin_username, 
            admin_password=get_password_hash(tenant_in.admin_password)
        )
        db.add(db_tenant)
        db.flush()
        db_tenant_id = db_tenant.id
        db.commit()
        # db.refresh(db_tenant) -- REMOVED per multi-tenant best practice
        
        # Restore tenant search path (although usually public for global tenant registry)
        # But we were in public already. Let's be safe if we were in a specific context.
        # Actually create_tenant runs as superadmin, usually public.
        # But let's check db.info just in case.
        tenant_schema = db.info.get('tenant_schema')
        if tenant_schema:
            db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        else:
             # Default to public if not set (create_tenant usually starts in public)
             db.execute(text("SET search_path TO public"))

        db_tenant = db.query(Tenant).filter(Tenant.id == db_tenant_id).first()
        
        # 4. Seed Tenant Data
        with SessionLocal() as sdb:
            sdb.execute(text(f"SET search_path TO {schema_name}"))
            
            # 1. Base Data
            cats = [Category(name=n) for n in ["Antibiotics", "Analgesics", "Antivirals", "Narcotics", "Supplements"]]
            mans = [Manufacturer(name=n) for n in ["Pfizer", "GlaxoSmithKline", "Novartis", "Local Pharma"]]
            sups = [Supplier(name="Main Distributions", address="Global Hub", gst_number="GST-99901")]
            # Seed default store
            main_store = Store(name="Main Branch", address="Primary Hub", is_warehouse=False)
            sdb.add_all(cats + mans + sups + [main_store]); sdb.flush()

            # 2. Roles & Perms
            perms = [Permission(name=n) for n in ["manage_users", "manage_inventory", "manage_sales", "view_reports"]]
            sdb.add_all(perms); sdb.flush()
            
            admin_role = Role(name="Admin", description="Full Access", permissions=perms)
            cashier_role = Role(name="Cashier", description="Sales Only", permissions=[p for p in perms if p.name in ["manage_sales"]])
            sdb.add_all([admin_role, cashier_role]); sdb.flush()

            # 3. Admin User
            admin_user = User(username=tenant_in.admin_username, email=f"{tenant_in.admin_username}@{tenant_in.subdomain}.com", 
                              hashed_password=db_tenant.admin_password, roles=[admin_role], store_id=main_store.id)
            sdb.add(admin_user)
            
            # 4. Generics
            from ..models import Generic
            paracetamol = Generic(name="Paracetamol")
            sdb.add(paracetamol)
            sdb.flush()

            # 5. Sample Product
            sample_product = Product(
                product_name="Panadol CF",
                category_id=cats[1].id, 
                manufacturer_id=mans[2].id,
                generics_id=paracetamol.id,
                supplier_id=sups[0].id,
                retail_price=10.0,
                average_cost=5.0
            )
            sdb.add(sample_product); sdb.flush()
            sdb.add(StockInventory(
                product_id=sample_product.id, store_id=main_store.id, batch_number="BN-101", 
                expiry_date=datetime.now()+timedelta(days=365),
                unit_cost=5.0, selling_price=9.5, 
                quantity=200, grn_id=None
            ))
            
            # 6. Seed Chart of Accounts
            from ..models.accounting_models import Account, AccountType
            
            default_accounts = [
                # ASSETS (1000-1999)
                {"code": "1000", "name": "Cash", "type": AccountType.ASSET, "parent": None},
                {"code": "1100", "name": "Bank Account", "type": AccountType.ASSET, "parent": None},
                {"code": "1200", "name": "Accounts Receivable", "type": AccountType.ASSET, "parent": None},
                {"code": "1300", "name": "Inventory", "type": AccountType.ASSET, "parent": None},
                {"code": "1400", "name": "Prepaid Expenses", "type": AccountType.ASSET, "parent": None},
                {"code": "1500", "name": "Fixed Assets", "type": AccountType.ASSET, "parent": None},
                {"code": "1510", "name": "Furniture & Fixtures", "type": AccountType.ASSET, "parent": "1500"},
                {"code": "1520", "name": "Equipment", "type": AccountType.ASSET, "parent": "1500"},
                
                # LIABILITIES (2000-2999)
                {"code": "2000", "name": "Accounts Payable", "type": AccountType.LIABILITY, "parent": None},
                {"code": "2100", "name": "Salaries Payable", "type": AccountType.LIABILITY, "parent": None},
                {"code": "2200", "name": "Tax Payable", "type": AccountType.LIABILITY, "parent": None},
                {"code": "2300", "name": "Short-term Loans", "type": AccountType.LIABILITY, "parent": None},
                
                # EQUITY (3000-3999)
                {"code": "3000", "name": "Owner's Capital", "type": AccountType.EQUITY, "parent": None},
                {"code": "3100", "name": "Retained Earnings", "type": AccountType.EQUITY, "parent": None},
                {"code": "3200", "name": "Drawings", "type": AccountType.EQUITY, "parent": None},
                
                # REVENUE (4000-4999)
                {"code": "4000", "name": "Sales Revenue", "type": AccountType.REVENUE, "parent": None},
                {"code": "4100", "name": "Other Income", "type": AccountType.REVENUE, "parent": None},
                
                # EXPENSES (5000-5999)
                {"code": "5000", "name": "Cost of Goods Sold", "type": AccountType.EXPENSE, "parent": None},
                {"code": "5100", "name": "Salaries Expense", "type": AccountType.EXPENSE, "parent": None},
                {"code": "5200", "name": "Rent Expense", "type": AccountType.EXPENSE, "parent": None},
                {"code": "5300", "name": "Utilities Expense", "type": AccountType.EXPENSE, "parent": None},
                {"code": "5400", "name": "Discount Given", "type": AccountType.EXPENSE, "parent": None},
                {"code": "5500", "name": "Other Expenses", "type": AccountType.EXPENSE, "parent": None},
                {"code": "5600", "name": "Depreciation Expense", "type": AccountType.EXPENSE, "parent": None},
            ]
            
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
                sdb.add(account)
                sdb.flush()  # Get the ID
                account_map[acc_data["code"]] = account.id
            
            # Second pass: Update parent relationships
            for acc_data in default_accounts:
                if acc_data["parent"]:
                    account = sdb.query(Account).filter(
                        Account.account_code == acc_data["code"]
                    ).first()
                    if account:
                        account.parent_account_id = account_map.get(acc_data["parent"])
            
            sdb.commit()
        return db_tenant
    except Exception as e:
        traceback.print_exc()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[TenantResponse])
def list_tenants(db: Session = Depends(get_db), admin: SuperAdmin = Depends(get_current_superadmin)):
    db.execute(text("SET search_path TO public"))
    return db.query(Tenant).all()
