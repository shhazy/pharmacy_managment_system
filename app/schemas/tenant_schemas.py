from pydantic import BaseModel
from datetime import datetime

class TenantCreate(BaseModel):
    name: str
    subdomain: str
    admin_username: str
    admin_password: str

class TenantResponse(BaseModel):
    id: int
    name: str
    subdomain: str
    schema_name: str
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True
