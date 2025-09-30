"""User model definition."""

from datetime import datetime
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from . import db


VERIFICATION_STATUSES = ("unverified", "pending", "approved", "rejected")


class User(db.Model):
    """Represents a platform user."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="worker")
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    verification_status = db.Column(
        db.String(32),
        nullable=False,
        default="unverified",
        server_default=db.text("'unverified'"),
    )
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.text("true"),
    )
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

    def mark_verified(self) -> None:
        """Mark the user as verified and approved."""

        self.is_verified = True
        self.verification_status = "approved"

    def mark_unverified(self, note: Optional[str] = None) -> None:
        """Mark the user as unverified with an optional note."""

        self.is_verified = False
        self.verification_status = note or "unverified"

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User {self.email}>"
