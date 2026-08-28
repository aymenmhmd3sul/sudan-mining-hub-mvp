from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

def test_security_module():
    print("--- بدء فحص وحدة الأمان والتشفير النظيفة ---")
    
    # 1. اختبار تشفير وفحص كلمة المرور
    raw_pwd = "SecretPassword123!"
    hashed = get_password_hash(raw_pwd)
    assert verify_password(raw_pwd, hashed), "فشل التحقق من كلمة المرور المشفّرة!"
    assert not verify_password("WrongPassword", hashed), "تم قبول كلمة مرور خاطئة!"
    hashed_again = get_password_hash(raw_pwd)
    assert hashed != hashed_again, "Salt is not random!"
    print("[1/2] تم التشفير والتحقق من كلمة المرور بنجاح.")

    # 2. اختبار توليد وفك تشفير Token
    payload = {"sub": "test@sudanmining.com", "role": "MERCHANT"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded["sub"] == payload["sub"]
    assert decoded["role"] == payload["role"]
    print(f"[2/2] تم توليد وفك الـ JWT Token بنجاح: {token[:30]}...")

if __name__ == "__main__":
    test_security_module()
