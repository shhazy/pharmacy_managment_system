from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import traceback

from .database import engine, Base, SessionLocal
from .models import Tenant, SuperAdmin
from .auth import get_password_hash
from .routes import api_router

app = FastAPI(title="Pro Pharmacy ERP API")

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# GLOBAL EXCEPTION HANDLER
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )
    
    traceback.print_exc()
    return JSONResponse(
        status_code=500,  # Use 500 for real crashes
        content={"detail": f"INTERNAL SERVER ERROR: {str(exc)}"},
    )

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend is running"}

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://pharmacymanagmentsystem-production.up.railway.app",
    ],
    allow_origin_regex=r"http://.*\.localhost:5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routes
app.include_router(api_router)

# --- STARTUP ---
@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine, tables=[Tenant.__table__, SuperAdmin.__table__])
        db = SessionLocal()
        try:
            db.execute(text("SET search_path TO public"))
            admin = db.query(SuperAdmin).filter(SuperAdmin.username == "admin").first()
            if not admin:
                db.add(SuperAdmin(username="admin", email="admin@pharmaconnect.com", hashed_password=get_password_hash("admin123")))
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"ERROR during startup: {e}")
        traceback.print_exc()
