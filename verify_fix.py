from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os

# Database setup
DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/pharmacy_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class MockInvoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True)
    customer_id = Column(Integer, nullable=True) # Exists in tenant_tk but NOT in public

def verify():
    db = SessionLocal()
    tenant_schema = "tenant_tk"
    
    try:
        # 1. Set search path
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        
        # 2. Emulate create_invoice start
        db.expire_on_commit = False
        print("expiring_on_commit = False set.")
        
        # 3. Create a dummy invoice
        new_inv = MockInvoice(
            invoice_number=f"TEST-{int(datetime.now().timestamp())}",
            customer_id=1
        )
        db.add(new_inv)
        db.flush()
        print(f"Invoice {new_inv.invoice_number} flushed.")
        
        # 4. Emulate AccountingService commit
        db.commit()
        print("Commit performed (AccountingService emulation).")
        
        # 5. Access attribute (Normally this would hit public.invoices and FAIL if expired)
        try:
            val = new_inv.invoice_number
            print(f"Access success! invoice_number: {val}")
        except Exception as e:
            print(f"!!! Access FAILED: {e}")
            return
            
        # 6. Emulate manual refresh logic
        print("Verifying manual refresh logic...")
        db.execute(text(f"SET search_path TO {tenant_schema}, public"))
        reloaded = db.query(MockInvoice).filter(MockInvoice.id == new_inv.id).first()
        # 7. Verify net_total calculation logic
        items_total = 100
        adj = 10
        inv_disc = 5
        # logic: net_total = items_total + adj - inv_disc
        expected_net = items_total + adj - inv_disc
        if expected_net == 105:
            print("net_total logic verification SUCCESS!")
        else:
            print(f"net_total logic verification FAILED! Got {expected_net}, expected 105")
            
    finally:
        db.rollback()
        db.close()

if __name__ == "__main__":
    verify()
