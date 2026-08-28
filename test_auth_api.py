from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_auth_endpoints():
    print("--- بدء اختبار API التسجيل والدخول ---")
    
    # 1. اختبار تسجيل حساب agent (وكيل)
    reg_payload = {
        "email": "agent_test@sudanmining.com",
        "password": "Password123!",
        "full_name": "عثمان الوكيل",
        "phone_number": "+249123456789",
        "role": "AGENT"
    }
    reg_resp = client.post("/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, f"فشل التسجيل: {reg_resp.text}"
    user_data = reg_resp.json()
    assert user_data["role"] == "AGENT", f"خطأ في تعيين الدور: {user_data['role']}"
    print(f"[1/2] تم تسجيل الحساب بنجاح بدور: {user_data['role']}")

    # 2. اختبار تسجيل الدخول
    login_payload = {
        "email": "agent_test@sudanmining.com",
        "password": "Password123!"
    }
    login_resp = client.post("/auth/login", json=login_payload)
    assert login_resp.status_code == 200, f"فشل الدخول: {login_resp.text}"
    token_data = login_resp.json()
    assert "access_token" in token_data
    print(f"[2/2] تم تسجيل الدخول واستلام الـ Token بنجاح.")

if __name__ == "__main__":
    test_auth_endpoints()
