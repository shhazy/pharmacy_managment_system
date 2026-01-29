from pydantic import BaseModel, EmailStr
from typing import List, Optional

class PermissionResponse(BaseModel):
    id: int
    name: str
    module: Optional[str] = None
    action: Optional[str] = None
    class Config: from_attributes = True

class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: List[PermissionResponse] = []
    class Config: from_attributes = True

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permission_ids: List[int] = []

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role_names: List[str]

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role_names: Optional[List[str]] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    roles: List[RoleResponse] = []
    class Config: from_attributes = True
