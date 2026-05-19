"""
Secure Cloud Onboarding Tool — MedGuardian Admin CLI.
Runs locally to safely onboard new hospital tenants onto your live cloud server.
"""
import requests
import json
import re

# Live Server URL configuration
LIVE_BACKEND_URL = "https://medgaurdian-backend.onrender.com"
SUPER_ADMIN_EMAIL = "ceo@medguardian.org"
SUPER_ADMIN_PASSWORD = "master123"

def onboard_new_tenant():
    print("=" * 60)
    print(" 🏥  MEDGUARDIAN SECURE TENANT ONBOARDING WIZARD  🛡️")
    print("=" * 60)
    
    # 1. Gather Hospital profile
    print("\n[+] Enter New Hospital Information:")
    name = input("    Hospital Name (e.g. Fortis Healthcare): ").strip()
    reg_number = input("    Registration ID (e.g. FORTIS-REG-01): ").strip()
    state = input("    State (e.g. Maharashtra): ").strip()
    district = input("    District (e.g. Mumbai): ").strip()
    address = input("    Address: ").strip()
    pincode = input("    Pincode: ").strip()
    
    # 2. Gather Administrator profile
    print("\n[+] Create Primary Hospital Administrator:")
    admin_name = input("    Admin Full Name (e.g. Dr. Ramesh Mehta): ").strip()
    admin_email = input("    Admin Official Email: ").strip()
    admin_password = input("    Admin Password (strong): ").strip()
    
    if not (name and reg_number and admin_email and admin_password):
        print("\n[❌] Error: Hospital Name, Registration ID, Admin Email and Password are mandatory!")
        return

    print("\n[*] Step 1: Performing secure Super Admin authorization handshake...")
    
    # Fetch JWT token
    try:
        login_res = requests.post(
            f"{LIVE_BACKEND_URL}/api/auth/login",
            data={
                "username": SUPER_ADMIN_EMAIL,
                "password": SUPER_ADMIN_PASSWORD
            },
            timeout=15
        )
        
        if login_res.status_code != 200:
            print(f"[❌] Auth Failed (HTTP {login_res.status_code}): {login_res.text}")
            return
            
        token = login_res.json()["access_token"]
        print("[✅] Authorization successful! Master JWT Token acquired.")
        
    except Exception as e:
        print(f"[❌] Connection Error: Could not connect to live backend. {e}")
        return

    # 3. Post onboarding request
    print("\n[*] Step 2: Provisioning new isolated hospital tenant in the cloud...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": name,
        "registration_number": reg_number,
        "state": state,
        "district": district,
        "address": address,
        "pincode": pincode,
        "admin_name": admin_name,
        "admin_email": admin_email,
        "admin_password": admin_password
    }
    
    try:
        onboard_res = requests.post(
            f"{LIVE_BACKEND_URL}/api/auth/onboard-hospital",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if onboard_res.status_code != 201:
            error_details = onboard_res.json().get("detail", onboard_res.text)
            print(f"[❌] Onboarding Failed (HTTP {onboard_res.status_code}): {error_details}")
            return
            
        data = onboard_res.json()
        print("\n" + "=" * 60)
        print(" 🎉  HOSPITAL TENANT SUCCESSFULLY PROVISIONED!  🚀")
        print("=" * 60)
        print(f"    🏥  Hospital Name : {name}")
        print(f"    🔑  Hospital ID   : {data['hospital_id']}")
        print(f"    👤  Admin Account : {admin_email}")
        print(f"    🔑  Admin Password: {admin_password}")
        print("-" * 60)
        print(" 👉  To log in and test, visit your live cockpit:")
        print("     https://medgaurdian.onrender.com")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"[❌] Transmission Error: Failed to complete onboarding sequence. {e}")

if __name__ == "__main__":
    onboard_new_tenant()
