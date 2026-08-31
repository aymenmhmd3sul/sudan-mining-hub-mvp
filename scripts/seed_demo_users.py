from app.db.session import SessionLocal
from app.models.user import UserModel, UserRole
from app.core.security import get_password_hash

DEMO_PASSWORD = "Test1234!"

DEMO_USERS = [
    {
        "email": "merchant1.demo@example.com",
        "full_name": "Demo Merchant 1",
        "phone_number": "0900000001",
        "role": UserRole.MERCHANT,
    },
    {
        "email": "merchant2.demo@example.com",
        "full_name": "Demo Merchant 2",
        "phone_number": "0900000002",
        "role": UserRole.MERCHANT,
    },
    {
        "email": "buyer1.demo@example.com",
        "full_name": "Demo Buyer 1",
        "phone_number": "0900000011",
        "role": UserRole.BUYER,
    },
    {
        "email": "buyer2.demo@example.com",
        "full_name": "Demo Buyer 2",
        "phone_number": "0900000012",
        "role": UserRole.BUYER,
    },
]


def main():
    db = SessionLocal()

    try:
        password_hash = get_password_hash(DEMO_PASSWORD)

        for data in DEMO_USERS:
            existing = (
                db.query(UserModel)
                .filter(UserModel.email == data["email"])
                .first()
            )

            if existing:
                print(f"EXISTS: {data['email']}")
                continue

            user = UserModel(
                email=data["email"],
                hashed_password=password_hash,
                full_name=data["full_name"],
                phone_number=data["phone_number"],
                role=data["role"],
                is_approved=True,
            )

            db.add(user)
            print(f"CREATE: {data['email']} [{data['role'].value}]")

        db.commit()

        print("===== DEMO USERS SEED PASS =====")
        print("MERCHANTS: 2")
        print("BUYERS: 2")
        print("PASSWORD: Test1234!")

    finally:
        db.close()


if __name__ == "__main__":
    main()
