"""User model definition."""

from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from . import db


class User(db.Model):
    """Represents a platform user."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="worker")
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    subscription = db.relationship(
        "EmployerSubscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        """Hash and store the password."""

        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""

        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User {self.email}>"
