from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmacy_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        print("DEBUG: get_db called, setting path to public")
        db.execute(text("SET search_path TO public"))
        yield db
    except Exception as e:
        print(f"DEBUG: get_db FAILED: {e}")
        raise e
    finally:
        db.close()

def get_tenant_db(tenant_schema: str):
    db = SessionLocal()
    try:
        # Set the search path to the tenant's schema
        db.execute(text(f"SET search_path TO {tenant_schema}"))
        yield db
    finally:
        db.close()

def create_tenant_schema(schema_name: str):
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        conn.commit()
