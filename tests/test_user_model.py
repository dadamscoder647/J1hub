"""Tests for the User model helpers."""

from models import db
from models.user import User


def test_user_verification_helpers(app):
    """Ensure helper methods toggle verification state as expected."""

    with app.app_context():
        user = User(email="helper@example.com", role="worker")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        assert user.is_active is True
        assert user.verification_status == "unverified"
        assert user.is_verified is False

        user.mark_verified()
        db.session.commit()
        db.session.refresh(user)

        assert user.is_verified is True
        assert user.verification_status == "approved"

        note = "awaiting documents"
        user.mark_unverified(note=note)
        db.session.commit()
        db.session.refresh(user)

        assert user.is_verified is False
        assert user.verification_status == note

        user.mark_unverified()
        db.session.commit()
        db.session.refresh(user)

        assert user.verification_status == "unverified"


def test_user_table_columns_are_unique_and_expected():
    """Ensure the users table metadata defines each expected column exactly once."""

    column_names = [column.name for column in User.__table__.columns]

    assert len(column_names) == len(set(column_names))
    assert column_names == [
        "id",
        "email",
        "password_hash",
        "role",
        "is_verified",
        "verification_status",
        "is_active",
        "created_at",
    ]
