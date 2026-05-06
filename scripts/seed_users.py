from _bootstrap import add_project_root

add_project_root()

from app.core.passwords import hash_password
from app.db.session import SessionLocal
from app.models.user import User

DEFAULT_PW = "TestPassword123!"

def run():
    db = SessionLocal()
    try:
        # upsert by user_id
        users = [
            User(
                user_id="U001",
                email="admin@company.com",
                password_hash=hash_password(DEFAULT_PW),
                role="admin",
                status="active",
                must_change_password=True,
            ),
            User(
                user_id="U002",
                email="marketer@company.com",
                password_hash=hash_password(DEFAULT_PW),
                role="marketer",
                status="active",
                must_change_password=True,
            ),
            User(
                user_id="U003",
                email="viewer@company.com",
                password_hash=hash_password(DEFAULT_PW),
                role="viewer",
                status="active",
                must_change_password=True,
            ),
        ]

        for u in users:
            existing = db.query(User).filter(User.user_id == u.user_id).first()
            if existing:
                existing.email = u.email
                existing.password_hash = u.password_hash
                existing.role = u.role
                existing.status = u.status
                existing.must_change_password = u.must_change_password
            else:
                db.add(u)

        db.commit()
        print("Seed users OK")
    finally:
        db.close()

if __name__ == "__main__":
    run()
