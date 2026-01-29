# Routes package
from fastapi import APIRouter
from .auth_routes import router as auth_router
from .tenant_routes import router as tenant_router
from .inventory_routes import router as inventory_router
from .medicine_routes import router as medicine_router
from .procurement_routes import router as procurement_router
from .sales_routes import router as sales_router
from .analytics_routes import router as analytics_router
from .user_routes import router as user_router
from .role_routes import router as role_router
from .permission_routes import router as permission_router
from .common_routes import router as common_router
from .inventory_crud_routes import router as inventory_crud_router
from .inventory_adjustment_routes import router as inventory_adjustment_router
from .product_routes import router as product_router
from .accounting_routes import router as accounting_router

# Create main router
api_router = APIRouter()

# Include all route modules
api_router.include_router(auth_router, tags=["Authentication"])
api_router.include_router(tenant_router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(medicine_router, prefix="/medicines", tags=["Medicines"])
api_router.include_router(procurement_router, prefix="/procurement", tags=["Procurement"])
api_router.include_router(sales_router, prefix="/sales", tags=["Sales"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(user_router, prefix="/users", tags=["Users"])
api_router.include_router(role_router, prefix="/roles", tags=["Roles"])
api_router.include_router(permission_router, prefix="/permissions", tags=["Permissions"])
api_router.include_router(common_router, tags=["Common"])
api_router.include_router(inventory_crud_router, prefix="/inventory", tags=["Inventory CRUD"])
api_router.include_router(inventory_adjustment_router, prefix="/inventory", tags=["Inventory Adjustment"])
api_router.include_router(product_router, prefix="/products", tags=["Products"])
api_router.include_router(accounting_router)


__all__ = ["api_router"]

