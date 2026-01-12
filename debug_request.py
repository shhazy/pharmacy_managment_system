import requests
import json

def test_login():
    url = "http://localhost:8000/auth/login"
    payload = {
        "username": "testadmin",
        "password": "wrongpassword",
        "tenant_id": "test"
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        print(f"Sending POST to {url} with payload: {payload}")
        res = requests.post(url, json=payload, headers=headers)
        
        print(f"Status Code: {res.status_code}")
        print("Response Body:")
        print(res.text)
        
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_login()
