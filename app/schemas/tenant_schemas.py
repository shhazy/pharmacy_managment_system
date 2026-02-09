from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TenantCreate(BaseModel):
    name: str
    subdomain: str
    admin_username: str
    admin_password: str
    is_trial: Optional[bool] = False
    trial_end_date: Optional[datetime] = None

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    is_trial: Optional[bool] = None
    trial_end_date: Optional[datetime] = None

class TenantResponse(BaseModel):
    id: int
    name: str
    subdomain: str
    schema_name: str
    is_active: bool
    is_trial: bool
    trial_end_date: Optional[datetime]
    created_at: datetime
    class Config: from_attributes = True
