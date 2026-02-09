from sqlalchemy import create_engine, text
import json

DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
engine = create_engine(DATABASE_URL)

def check_invoice():
    with engine.connect() as conn:
        print("Checking Invoice: INV-000051 in tenant_tk")
        query = text("""
            SELECT ii.*, p.product_name 
            FROM tenant_tk.invoice_items ii
            JOIN public.products p ON ii.medicine_id = p.id
            WHERE ii.invoice_id = (SELECT id FROM tenant_tk.invoices WHERE invoice_number = 'INV-000051')
        """)
        results = conn.execute(query).all()
        
        for row in results:
            print(f"Product: {row.product_name}")
            print(f"  Qty: {row.quantity}, Price: {row.unit_price}")
            print(f"  Discount %: {row.discount_percent}, Discount Amt: {row.discount_amount}")
            print(f"  Total Price: {row.total_price}")
            
        inv_query = text("SELECT * FROM tenant_tk.invoices WHERE invoice_number = 'INV-000051'")
        inv = conn.execute(inv_query).first()
        if inv:
            print(f"\nInvoice Total: {inv.net_total}, Subtotal: {inv.sub_total}, Tax: {inv.tax_amount}, Discount: {inv.discount_amount}")

if __name__ == "__main__":
    check_invoice()
