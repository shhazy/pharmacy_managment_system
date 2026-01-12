from sqlalchemy import create_engine, text
engine = create_engine("postgresql://postgres:1234@localhost:5432/pharmacy_db")
with engine.connect() as conn:
    res = conn.execute(text("SELECT subdomain, schema_name FROM public.tenants"))
    for row in res:
        print(f"Tenant: {row[0]}, Schema: {row[1]}")
        tables = conn.execute(text(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{row[1]}'"))
        print(f"  Tables: {[t[0] for t in tables]}")
