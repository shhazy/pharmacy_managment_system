from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime, timedelta

from ..models import Invoice, StockInventory, Product, User
from ..auth import get_db_with_tenant, get_current_tenant_user

router = APIRouter()

@router.get("/profit-margin")
def get_profit_data(db: Session = Depends(get_db_with_tenant)):
    results = db.execute(text("""
        SELECT p.product_name, SUM(ii.quantity * (ii.unit_price - si.unit_cost)) as profit
        FROM invoice_items ii
        JOIN products p ON ii.medicine_id = p.id
        JOIN stock_inventory si ON ii.batch_id = si.inventory_id
        GROUP BY p.product_name
        ORDER BY profit DESC LIMIT 10
    """)).fetchall()
    return [{"medicine": r[0], "total_profit": r[1]} for r in results]

@router.get("/top-selling")
def top_selling(db: Session = Depends(get_db_with_tenant)):
    results = db.execute(text("""
        SELECT p.product_name, SUM(ii.quantity) as total_qty
        FROM invoice_items ii
        JOIN products p ON ii.medicine_id = p.id
        GROUP BY p.product_name
        ORDER BY total_qty DESC LIMIT 10
    """)).fetchall()
    return [{"medicine": r[0], "units_sold": r[1]} for r in results]

@router.get("/slow-moving")
def slow_moving(db: Session = Depends(get_db_with_tenant)):
    results = db.execute(text("""
        SELECT p.product_name, SUM(si.quantity) as stock
        FROM products p
        JOIN stock_inventory si ON p.id = si.product_id
        WHERE p.id NOT IN (SELECT medicine_id FROM invoice_items WHERE created_at > NOW() - INTERVAL '30 days')
        GROUP BY p.product_name
        HAVING SUM(si.quantity) > 0
    """)).fetchall()
    return [{"medicine": r[0], "current_stock": r[1]} for r in results]

@router.get("/daily-sales")
def get_daily_sales(db: Session = Depends(get_db_with_tenant), user: User = Depends(get_current_tenant_user)):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sales = db.query(func.sum(Invoice.net_total)).filter(Invoice.created_at >= today).scalar() or 0
    count = db.query(func.count(Invoice.id)).filter(Invoice.created_at >= today).scalar() or 0
    return {"total_sales": sales, "invoice_count": count}

@router.get("/expiry-alerts")
def get_expiry_alerts(db: Session = Depends(get_db_with_tenant)):
    next_90_days = datetime.utcnow() + timedelta(days=90)
    return db.query(StockInventory).join(Product).filter(
        StockInventory.expiry_date <= next_90_days, 
        StockInventory.quantity > 0
    ).all()

@router.get("/low-stock")
def get_low_stock(db: Session = Depends(get_db_with_tenant)):
    return db.query(Product).join(StockInventory).group_by(Product.id).having(
        func.sum(StockInventory.quantity) <= Product.reorder_level
    ).all()
