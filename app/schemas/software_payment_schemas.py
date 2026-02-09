from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SoftwarePaymentBase(BaseModel):
    valid_from: datetime
    valid_to: datetime

class SoftwarePaymentCreate(SoftwarePaymentBase):
    receipt_path: str

class SoftwarePaymentUpdate(BaseModel):
    status: str
    rejection_reason: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None

class SoftwarePaymentResponse(SoftwarePaymentBase):
    id: int
    tenant_id: int
    receipt_path: str
    status: str
    rejection_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
