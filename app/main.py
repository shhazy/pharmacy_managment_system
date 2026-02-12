from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
import traceback

from .database import engine, Base, SessionLocal
from .models import Tenant, SuperAdmin, SoftwarePayment
from .auth import get_password_hash
from .routes import api_router

app = FastAPI(title="Pro Pharmacy ERP API")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*", # Allow all http/https origins properly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)
# GLOBAL EXCEPTION HANDLER
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin")
    headers = {}
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=headers
        )
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
            headers=headers
        )
    
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"INTERNAL SERVER ERROR: {str(exc)}"},
        headers=headers
    )

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend is running"}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    origin = request.headers.get("origin")
    print(f"DEBUG: Request {request.method} {request.url.path} from Origin: {origin}")
    response = await call_next(request)
    return response

# app.add_middleware(
#     CORSMiddleware,
#     allow_origin_regex=r".*",
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# Include all routes
app.include_router(api_router)

# --- STARTUP ---
@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine, tables=[Tenant.__table__, SuperAdmin.__table__, SoftwarePayment.__table__])
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

