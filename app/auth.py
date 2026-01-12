from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from .database import get_db, SessionLocal
from .models import User, Tenant
from sqlalchemy import text

import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY_CHANGE_ME")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

import bcrypt

def verify_password(plain_password, hashed_password):
    if not hashed_password: return False
    # Bcrypt requires bytes
    password_bytes = plain_password.encode('utf-8')
    # If hashed_password is a string (from DB), encode it
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(password_bytes, hashed_password)
    except Exception:
        return False

def get_password_hash(password):
    # Bcrypt requires bytes
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

from fastapi.security import OAuth2PasswordBearer
from .models import User, Tenant, SuperAdmin, Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user_data(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception

async def get_current_superadmin(
    payload: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db)
):
    if not payload.get("is_superadmin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    admin = db.query(SuperAdmin).filter(SuperAdmin.username == payload.get("sub")).first()
    if admin is None:
        raise HTTPException(status_code=401, detail="Invalid admin")
    return admin

def get_db_with_tenant(x_tenant_id: str = Header(None)):
    db = SessionLocal()
    print(f"AUTH DEBUG: get_db_with_tenant called with X-Tenant-ID: '{x_tenant_id}'")
    try:
        if not x_tenant_id:
             print("AUTH DEBUG: No X-Tenant-ID provided, using 'public'")
             db.execute(text(f"SET search_path TO public"))
             yield db
             return

        # Find tenant by subdomain
        tenant = db.query(Tenant).filter(Tenant.subdomain == x_tenant_id).first()
        if not tenant:
            print(f"AUTH DEBUG: Tenant '{x_tenant_id}' NOT FOUND")
            raise HTTPException(status_code=404, detail=f"Tenant '{x_tenant_id}' not found")
            
        print(f"AUTH DEBUG: Setting search_path to '{tenant.schema_name}, public'")
        db.execute(text(f"SET search_path TO {tenant.schema_name}, public"))
        yield db
    finally:
        db.close()

async def get_current_tenant_user(
    x_tenant_id: str = Header(...),
    payload: dict = Depends(get_current_user_data),
    db: Session = Depends(get_db_with_tenant)
):
    try:
        if payload.get("tenant_id") != x_tenant_id:
            print(f"AUTH DEBUG: Payload tenant '{payload.get('tenant_id')}' != Header tenant '{x_tenant_id}'")
            raise HTTPException(status_code=403, detail="Not authorized for this tenant")
        
        user = db.query(User).filter(User.username == payload.get("sub")).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Accessing roles here to ensure they are loaded while session is open
        _ = user.roles
        return user
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"AUTH ERROR in get_current_tenant_user: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Authentication error")
