from app.schemas.user import UserCreate, UserOut, UserRole

def test_user_schemas():
    print("--- بدء فحص مخططات Pydantic ---")
    
    # تجربة إنشاء بيانات تسجيل صحيحة
    user_in = UserCreate(
        email="test_schema@sudanmining.com",
        password="securepassword123",
        full_name="عمر التاجر",
        role=UserRole.MERCHANT
    )
    
    assert user_in.role == UserRole.MERCHANT
    print(f"[نجاح المخطط]: تم التحقق من إنشاء مدخلات المستخدم ({user_in.email}) بدور {user_in.role.value}")

if __name__ == "__main__":
    test_user_schemas()
