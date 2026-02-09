from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text, or_, func
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from ..models import Customer, CustomerType, CustomerGroup, User, CustomerLedger
from ..schemas.customer_schemas import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    CustomerTypeCreate, CustomerTypeUpdate, CustomerTypeResponse,
    CustomerGroupCreate, CustomerGroupUpdate, CustomerGroupResponse
)
from ..auth import get_db_with_tenant, get_current_tenant_user
from ..schemas.common_schemas import PaginatedResponse
from ..utils.pagination import paginate

router = APIRouter()

# --- Helpers ---

def add_balances_to_customers(db: Session, customers: List[Customer]):
    if not customers:
        return
        
    customer_ids = [c.id for c in customers]
    
    # Batch calculate balances
    balance_results = db.query(
        CustomerLedger.customer_id,
        (func.sum(CustomerLedger.debit_amount) - func.sum(CustomerLedger.credit_amount)).label('ledger_balance')
    ).filter(CustomerLedger.customer_id.in_(customer_ids)).group_by(CustomerLedger.customer_id).all()
    
    balances_map = {res.customer_id: float(res.ledger_balance or 0.0) for res in balance_results}
    
    for c in customers:
        c.current_balance = (c.opening_balance or 0.0) + balances_map.get(c.id, 0.0)

# --- Customer Group Routes ---

@router.get("/groups", response_model=PaginatedResponse[CustomerGroupResponse])
def list_customer_groups(
    page: int = 1, 
    page_size: int = 10, 
    search: Optional[str] = None,
    db: Session = Depends(get_db_with_tenant),
    user: User = Depends(get_current_tenant_user)
):
    query = db.query(CustomerGroup).filter(CustomerGroup.is_active == True)
    if search:
        query = query.filter(CustomerGroup.name.ilike(f"%{search}%"))
    
    items, total, total_pages = paginate(query.order_by(CustomerGroup.id.desc()), page, page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/groups/all", response_model=List[CustomerGroupResponse])
def list_all_customer_groups(db: Session = Depends(get_db_with_tenant)):
    return db.query(CustomerGroup).filter(CustomerGroup.is_active == True).all()

@router.post("/groups", response_model=CustomerGroupResponse)
def create_customer_group(group: CustomerGroupCreate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_group = CustomerGroup(**group.dict(), created_by=user.id, updated_by=user.id)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

@router.put("/groups/{group_id}", response_model=CustomerGroupResponse)
def update_customer_group(group_id: int, group: CustomerGroupUpdate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_group = db.query(CustomerGroup).filter(CustomerGroup.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Customer group not found")
    
    for field, value in group.dict(exclude_unset=True).items():
        setattr(db_group, field, value)
    
    db_group.updated_by = user.id
    db.commit()
    db.refresh(db_group)
    return db_group

@router.delete("/groups/{group_id}")
def delete_customer_group(group_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_group = db.query(CustomerGroup).filter(CustomerGroup.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Customer group not found")
    
    db_group.is_active = False
    db_group.updated_by = user.id
    db.commit()
    return {"message": "Customer group deleted successfully"}

# --- Customer Type Routes ---

@router.get("/types", response_model=PaginatedResponse[CustomerTypeResponse])
def list_customer_types(
    page: int = 1, 
    page_size: int = 10, 
    search: Optional[str] = None,
    db: Session = Depends(get_db_with_tenant),
    user: User = Depends(get_current_tenant_user)
):
    query = db.query(CustomerType).filter(CustomerType.is_active == True)
    if search:
        query = query.filter(CustomerType.name.ilike(f"%{search}%"))
    
    items, total, total_pages = paginate(query.order_by(CustomerType.id.desc()), page, page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/types/all", response_model=List[CustomerTypeResponse])
def list_all_customer_types(db: Session = Depends(get_db_with_tenant)):
    return db.query(CustomerType).filter(CustomerType.is_active == True).all()

@router.post("/types", response_model=CustomerTypeResponse)
def create_customer_type(type_in: CustomerTypeCreate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_type = CustomerType(**type_in.dict(), created_by=user.id, updated_by=user.id)
    db.add(db_type)
    db.commit()
    db.refresh(db_type)
    return db_type

@router.put("/types/{type_id}", response_model=CustomerTypeResponse)
def update_customer_type(type_id: int, type_in: CustomerTypeUpdate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_type = db.query(CustomerType).filter(CustomerType.id == type_id).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Customer type not found")
    
    for field, value in type_in.dict(exclude_unset=True).items():
        setattr(db_type, field, value)
    
    db_type.updated_by = user.id
    db.commit()
    db.refresh(db_type)
    return db_type

@router.delete("/types/{type_id}")
def delete_customer_type(type_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_type = db.query(CustomerType).filter(CustomerType.id == type_id).first()
    if not db_type:
        raise HTTPException(status_code=404, detail="Customer type not found")
    
    db_type.is_active = False
    db_type.updated_by = user.id
    db.commit()
    return {"message": "Customer type deleted successfully"}

# --- Customer Routes ---

@router.get("/", response_model=PaginatedResponse[CustomerResponse])
def list_customers(
    page: int = 1, 
    page_size: int = 10, 
    search: Optional[str] = None,
    type_id: Optional[int] = None,
    group_id: Optional[int] = None,
    db: Session = Depends(get_db_with_tenant),
    user: User = Depends(get_current_tenant_user)
):
    query = db.query(Customer).filter(Customer.is_active == True).options(
        joinedload(Customer.customer_type),
        joinedload(Customer.customer_group)
    )
    
    if search:
        query = query.filter(or_(
            Customer.name.ilike(f"%{search}%"),
            Customer.customer_code.ilike(f"%{search}%"),
            Customer.mobile_phone.ilike(f"%{search}%")
        ))
    
    if type_id:
        query = query.filter(Customer.type_id == type_id)
    if group_id:
        query = query.filter(Customer.group_id == group_id)
    
    items, total, total_pages = paginate(query.order_by(Customer.id.desc()), page, page_size)
    add_balances_to_customers(db, items)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

@router.get("/all", response_model=List[CustomerResponse])
def list_all_customers(db: Session = Depends(get_db_with_tenant)):
    customers = db.query(Customer).filter(Customer.is_active == True).options(
        joinedload(Customer.customer_type),
        joinedload(Customer.customer_group)
    ).all()
    add_balances_to_customers(db, customers)
    return customers

@router.post("/", response_model=CustomerResponse)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    try:
        db_customer = Customer(**customer.dict(), created_by=user.id, updated_by=user.id)
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
        
        # Reload with relationships
        return db.query(Customer).options(
            joinedload(Customer.customer_type),
            joinedload(Customer.customer_group)
        ).filter(Customer.id == db_customer.id).first()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db_with_tenant)):
    customer = db.query(Customer).options(
        joinedload(Customer.customer_type),
        joinedload(Customer.customer_group)
    ).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    add_balances_to_customers(db, [customer])
    return customer

@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, customer: CustomerUpdate, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    for field, value in customer.dict(exclude_unset=True).items():
        setattr(db_customer, field, value)
    
    db_customer.updated_by = user.id
    db_customer.updated_at = datetime.utcnow()
    db.commit()
    
    # Reload with relationships
    return db.query(Customer).options(
        joinedload(Customer.customer_type),
        joinedload(Customer.customer_group)
    ).filter(Customer.id == customer_id).first()

@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    db_customer.is_active = False
    db_customer.updated_by = user.id
    db_customer.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "Customer deleted successfully"}
