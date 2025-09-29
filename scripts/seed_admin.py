import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app
from models import db
from models.user import User


def main() -> None:
    app = create_app()
    with app.app_context():
        email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        password = os.getenv("ADMIN_PASSWORD", "AdminPass123")

        user = User.query.filter_by(email=email).first()
        if user:
            if user.role != "admin":
                user.role = "admin"
            if not user.check_password(password):
                user.set_password(password)
        else:
            user = User(email=email, role="admin", is_verified=True)
            user.set_password(password)
            db.session.add(user)

        db.session.commit()
        print(f"Admin user ensured: {email}")


if __name__ == "__main__":
    main()
