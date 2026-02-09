from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class SuperAdminResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

class SuperAdminUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
