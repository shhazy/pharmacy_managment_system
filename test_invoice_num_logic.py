import re

def generate_next_invoice_number(last_invoice_number):
    new_invoice_number = "INV-000001"
    if last_invoice_number:
        match = re.search(r'INV-(\d+)', last_invoice_number)
        if match:
            num_part = match.group(1)
            # Check if it's a sequence (e.g. 6 digits) vs timestamp (10+ digits)
            # If it's a timestamp (old format), we reset to 000001
            if len(num_part) < 10: 
                try:
                    next_seq = int(num_part) + 1
                    new_invoice_number = f"INV-{next_seq:06d}"
                except ValueError:
                    pass
    return new_invoice_number

def test_logic():
    print("Testing logic...")
    
    # Case 1: No previous invoice
    assert generate_next_invoice_number(None) == "INV-000001"
    print("Pass: None -> INV-000001")
    
    # Case 2: Previous invoice is INV-000001
    assert generate_next_invoice_number("INV-000001") == "INV-000002"
    print("Pass: INV-000001 -> INV-000002")
    
    # Case 3: Previous invoice is INV-000099
    assert generate_next_invoice_number("INV-000099") == "INV-000100"
    print("Pass: INV-000099 -> INV-000100")
    
    # Case 4: Previous invoice is old format (Timestamp)
    # e.g., INV-240101120000
    old_inv = "INV-240101120000"
    assert generate_next_invoice_number(old_inv) == "INV-000001"
    print(f"Pass: {old_inv} -> INV-000001")
    
    # Case 5: Previous invoice is unexpected format
    assert generate_next_invoice_number("INV-ABC") == "INV-000001"
    print("Pass: INV-ABC -> INV-000001")
    
    print("All logic tests passed.")

if __name__ == "__main__":
    test_logic()
