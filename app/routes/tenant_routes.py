from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from datetime import datetime, timedelta
import traceback

from ..database import engine, Base, get_db, SessionLocal
from ..models import (
    Tenant, User, Role, Product, SuperAdmin, Permission, 
    Batch, Category, Manufacturer, Supplier, Store
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
        db.commit()
        db.refresh(db_tenant)
        
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
            
            # 4. Sample Product
            sample_product = Product(
                product_name="Panadol CF", generic_name="Paracetamol", brand_name="Panadol",
                category_id=cats[1].id, manufacturer_id=mans[2].id, unit="Tablet", strength="500mg"
            )
            sdb.add(sample_product); sdb.flush()
            sdb.add(Batch(product_id=sample_product.id, store_id=main_store.id, batch_number="BN-101", 
                          expiry_date=datetime.now()+timedelta(days=365),
                          purchase_price=5.0, mrp=10.0, sale_price=9.5, 
                          current_stock=200, initial_stock=200))
            
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
