from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date

# --- Customer Group ---
class CustomerGroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class CustomerGroupCreate(CustomerGroupBase):
    pass

class CustomerGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class CustomerGroupResponse(CustomerGroupBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# --- Customer Type ---
class CustomerTypeBase(BaseModel):
    name: str
    description: Optional[str] = None

class CustomerTypeCreate(CustomerTypeBase):
    pass

class CustomerTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class CustomerTypeResponse(CustomerTypeBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# --- Customer ---
class CustomerBase(BaseModel):
    customer_code: str
    name: str
    type_id: Optional[int] = None
    group_id: Optional[int] = None
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    marital_status: Optional[str] = None
    ref_no: Optional[str] = None
    ref_name: Optional[str] = None
    ref_phone: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    phone_res: Optional[str] = None
    phone_off: Optional[str] = None
    mobile_phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    comments: Optional[str] = None
    mailing_status: bool = False
    ntn_no: Optional[str] = None
    gst_reg_no: Optional[str] = None
    cnic: Optional[str] = None
    occupation: Optional[str] = None
    alt_card_no: Optional[str] = None
    end_date: Optional[date] = None
    allow_credit: bool = False
    credit_limit: float = 0.0
    opening_balance: float = 0.0
    opening_amount: float = 0.0
    opening_date: Optional[date] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    customer_code: Optional[str] = None
    name: Optional[str] = None
    type_id: Optional[int] = None
    group_id: Optional[int] = None
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None
    marital_status: Optional[str] = None
    ref_no: Optional[str] = None
    ref_name: Optional[str] = None
    ref_phone: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    phone_res: Optional[str] = None
    phone_off: Optional[str] = None
    mobile_phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    comments: Optional[str] = None
    mailing_status: Optional[bool] = None
    ntn_no: Optional[str] = None
    gst_reg_no: Optional[str] = None
    cnic: Optional[str] = None
    occupation: Optional[str] = None
    alt_card_no: Optional[str] = None
    end_date: Optional[date] = None
    allow_credit: Optional[bool] = None
    credit_limit: Optional[float] = None
    opening_balance: Optional[float] = None
    opening_amount: Optional[float] = None
    opening_date: Optional[date] = None
    is_active: Optional[bool] = None

class CustomerResponse(CustomerBase):
    id: int
    current_balance: float = 0.0
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # Nested info if needed
    customer_type: Optional[CustomerTypeResponse] = None
    customer_group: Optional[CustomerGroupResponse] = None
    
    class Config:
        from_attributes = True
