"""Seed an administrator user."""

from app import create_app
from models import db
from models.user import User

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "AdminPass123"


def main() -> None:
    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(email=ADMIN_EMAIL).first()
        if admin is None:
            admin = User(
                email=ADMIN_EMAIL,
                role="admin",
                is_verified=True,
                verification_status="approved",
            )
            admin.set_password(ADMIN_PASSWORD)
            db.session.add(admin)
            action = "created"
        else:
            admin.role = "admin"
            admin.is_verified = True
            admin.verification_status = "approved"
            admin.set_password(ADMIN_PASSWORD)
            action = "updated"
        db.session.commit()
        print(f"Admin user {action}: {ADMIN_EMAIL}")


if __name__ == "__main__":
    main()
