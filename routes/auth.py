"""Authentication blueprint providing register and login endpoints."""

from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

from models import db
from models.user import User

ALLOWED_ROLES = {"worker", "employer", "admin"}

auth_bp = Blueprint("auth", __name__)


def _normalize_email(raw_email: str | None) -> str:
    """Normalize an email string by stripping whitespace and lowering case."""

    return (raw_email or "").strip().lower()


def _extract_role(raw_role: str | None) -> str:
    """Return a valid role string, defaulting to the model's default."""

    default_role = getattr(User.role.default, "arg", "worker")
    role = (raw_role or "").strip().lower() or default_role
    if role not in ALLOWED_ROLES:
        return ""
    return role


@auth_bp.route("/register", methods=["POST"])
def register() -> tuple:
    """Register a new user with an email, password, and optional role."""

    payload = request.get_json(silent=True) or {}
    email = _normalize_email(payload.get("email"))
    password = (payload.get("password") or "").strip()
    role = _extract_role(payload.get("role")) or getattr(User.role.default, "arg", "worker")

    if not email or not password:
        return (
            jsonify({"error": "Email and password are required."}),
            HTTPStatus.BAD_REQUEST,
        )

    if payload.get("role") and role not in ALLOWED_ROLES:
        return (
            jsonify({"error": "Role must be one of: worker, employer, admin."}),
            HTTPStatus.BAD_REQUEST,
        )

    if User.query.filter_by(email=email).first() is not None:
        return (
            jsonify({"error": "A user with that email already exists."}),
            HTTPStatus.CONFLICT,
        )

    user = User(email=email, role=role)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "User registered successfully.",
                "user": {"id": user.id, "email": user.email, "role": user.role},
            }
        ),
        HTTPStatus.CREATED,
    )


@auth_bp.route("/login", methods=["POST"])
def login() -> tuple:
    """Authenticate a user and return a JWT access token."""

    payload = request.get_json(silent=True) or {}
    email = _normalize_email(payload.get("email"))
    password = (payload.get("password") or "").strip()

    if not email or not password:
        return (
            jsonify({"error": "Email and password are required."}),
            HTTPStatus.BAD_REQUEST,
        )

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return (
            jsonify({"error": "Invalid email or password."}),
            HTTPStatus.UNAUTHORIZED,
        )

    access_token = create_access_token(identity=user.id)

    return (
        jsonify(
            {
                "access_token": access_token,
                "user": {"id": user.id, "email": user.email, "role": user.role},
            }
        ),
        HTTPStatus.OK,
    )
