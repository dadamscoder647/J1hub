"""Authentication routes."""

from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from sqlalchemy import func

from models.user import User

auth_bp = Blueprint("auth", __name__)


def _normalize_email(value: str | None) -> str | None:
    """Normalize an email address for comparison."""

    if value is None:
        return None
    return value.strip().lower()


def _serialize_user(user: User) -> dict[str, object]:
    """Return a lightweight representation of the user."""

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_verified": user.is_verified,
    }


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return a JWT access token."""

    payload = request.get_json(silent=True) or {}

    email = _normalize_email(payload.get("email"))
    password = payload.get("password")

    if not email or not password:
        return (
            jsonify({"error": "Email and password are required."}),
            HTTPStatus.BAD_REQUEST,
        )

    user = User.query.filter(func.lower(User.email) == email).first()

    if user is None or not user.check_password(password):
        return (
            jsonify({"error": "Invalid email or password."}),
            HTTPStatus.UNAUTHORIZED,
        )

    access_token = create_access_token(
        identity=str(user.id), additional_claims={"role": user.role}
    )

    return jsonify({"access_token": access_token, "user": _serialize_user(user)})
