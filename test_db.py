import sys
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.models.user import UserModel, UserRole

def run_local_db_test():
    print("--- بدء اختبار قاعدة البيانات المحلية ---")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(UserModel).filter(UserModel.email == "test_merchant@sudanmining.com").delete()
        db.commit()

        test_user = UserModel(
            email="test_merchant@sudanmining.com",
            hashed_password="fake_hashed_password_123",
            full_name="أحمد التاجر",
            phone_number="+249912345678",
            role=UserRole.MERCHANT
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)

        fetched_user = db.query(UserModel).filter(UserModel.email == "test_merchant@sudanmining.com").first()

        assert fetched_user is not None, "تعذر العثور على المستخدم!"
        assert fetched_user.is_approved is False, "is_approved يجب أن تكون False افتراضياً!"
        assert fetched_user.role == UserRole.MERCHANT, f"الدور المرجع خاطئ ({fetched_user.role})"

        print(f"[نجاح الاختبار المحلي 100%]")
        print(f"  - ID: {fetched_user.id}")
        print(f"  - البريد: {fetched_user.email}")
        print(f"  - الدور: {fetched_user.role.value}")
        print(f"  - الموافقة: {fetched_user.is_approved}")
    except Exception as e:
        print(f"[خطأ]: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_local_db_test()
