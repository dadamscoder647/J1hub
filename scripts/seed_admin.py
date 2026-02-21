"""Seed an administrator user."""

from app import create_app
from models import db
from models.user import User
from scripts.seed_credentials import (
    DEFAULT_ADMIN_EMAIL,
    DEFAULT_ADMIN_PASSWORD,
    get_seed_env_value,
)


def main() -> None:
    admin_email = get_seed_env_value(
        "seed_admin", "SEED_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL
    )
    admin_password = get_seed_env_value(
        "seed_admin", "SEED_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD
    )

    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(email=admin_email).first()
        if admin is None:
            admin = User(
                email=admin_email,
                role="admin",
                is_verified=True,
                verification_status="approved",
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            action = "created"
        else:
            admin.role = "admin"
            admin.is_verified = True
            admin.verification_status = "approved"
            admin.set_password(admin_password)
            action = "updated"
        db.session.commit()
        print(f"Admin user {action}: {admin_email}")


if __name__ == "__main__":
    main()
