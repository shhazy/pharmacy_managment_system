import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def debug_api():
    print("--- Debugging API Reports ---")
    
    # 1. Login to get token
    try:
        login_payload = {
            "username": "admin",
            "password": "password123", 
            "tenant_id": "tj" # Subdomain is passed as tenant_id in schema
        }
        
        # Correct endpoint from auth_routes.py
        resp = requests.post(f"{BASE_URL}/auth/login/", json=login_payload)
            
        if resp.status_code != 200:
            print(f"FATAL: Login failed: {resp.status_code} {resp.text}")
            return

        data = resp.json()
        token = data.get("access_token")
        tenant_id_from_login = data.get("tenant_id") # This is '1' (DB ID)
        
        # KEY FIX: The backend expects SUBDOMAIN in X-Tenant-ID header, not ID
        # In the real app, this comes from the URL subdomain or user context
        use_tenant_id = "tj" 
        
        print(f"Logged in. Token acquired. DB ID: {tenant_id_from_login}. Using Header X-Tenant-ID: {use_tenant_id}")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": use_tenant_id
        }
        
        # 2. Query Supplier Ledger Report
        # Get first supplier
        sup_resp = requests.get(f"{BASE_URL}/inventory/suppliers", headers=headers)
        print(f"Supplier Response Status: {sup_resp.status_code}")
        suppliers = sup_resp.json()
        print(f"Suppliers Data: {suppliers}")
        
        if not suppliers or not isinstance(suppliers, list) or len(suppliers) == 0:
            print("No suppliers found via API. Cannot query ledger.")
        else:
            first_sup_id = suppliers[0]['id']
            print(f"Querying ledger for Supplier ID {first_sup_id} ({suppliers[0]['name']})")
            
            # Query for Jan 2026
            params = {
                "from_date": "2026-01-01",
                "to_date": "2026-01-28"
            }
            
            report_resp = requests.get(
                f"{BASE_URL}/accounting/reports/supplier-ledger/{first_sup_id}",
                headers=headers,
                params=params
            )
            
            if report_resp.status_code == 200:
                report = report_resp.json()
                txns = report.get("transactions", [])
                print(f"API Returned {len(txns)} transactions.")
                for t in txns:
                    print(f" - {t['transaction_date']} | {t['transaction_type']} | {t['balance']}")
            else:
                print(f"Report API Failed: {report_resp.status_code} {report_resp.text}")

        # 3. Query Purchase Register
        print("Querying Purchase Register...")
        pr_resp = requests.get(
            f"{BASE_URL}/accounting/reports/purchase-register",
            headers=headers,
            params={"from_date": "2026-01-01", "to_date": "2026-01-28"}
        )
        if pr_resp.status_code == 200:
            pr = pr_resp.json()
            print(f"Purchase Register Items: {len(pr.get('items', []))}")
            for item in pr.get('items', []):
                print(f" - {item['date']} | {item['grn_number']} | {item['amount']}")
        else:
            print(f"Purchase Register API Failed: {pr_resp.status_code} {pr_resp.text}")

    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    debug_api()
