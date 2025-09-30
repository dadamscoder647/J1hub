"""Authentication blueprint providing register and login endpoints."""

from __future__ import annotations
from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from werkzeug.exceptions import BadRequest, Conflict, Unauthorized
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

from models import db
from models.user import User

# Use shared validator if available; otherwise fall back to plain get_json
try:
    from utils.request_validation import parse_json_request  # type: ignore
except Exception:  # pragma: no cover
    def parse_json_request(req):  # minimal fallback
        return req.get_json(silent=True) or {}

ALLOWED_ROLES = {"worker", "employer", "admin"}
auth_bp = Blueprint("auth", __name__)


def _normalize_email(raw_email: str | None) -> str:
    """Normalize an email string by stripping whitespace and lowering case."""
    return (raw_email or "").strip().lower()


def _extract_role(raw_role: str | None) -> str:
    """Return a valid role string, defaulting to the model's default."""
    default_role = getattr(User.role.default, "arg", "worker")
    role = (raw_role or "").strip().lower() or default_role
    return role if role in ALLOWED_ROLES else ""


@auth_bp.route("/register", methods=["POST"])
def register() -> tuple:
    """Register a new user with an email, password, and optional role."""
    payload = parse_json_request(request)
    email = _normalize_email(payload.get("email"))
    password = (payload.get("password") or "").strip()
    role = _extract_role(payload.get("role")) or getattr(User.role.default, "arg", "worker")

    if not email or not password:
        raise BadRequest("Email and password are required.")
    if payload.get("role") and role not in ALLOWED_ROLES:
        raise BadRequest("Role must be one of: worker, employer, admin.")

    # Case-insensitive unique check
    existing = User.query.filter(func.lower(User.email) == email).first()
    if existing is not None:
        raise Conflict("A user with that email already exists.")

    user = User(email=email, role=role)
    if hasattr(user, "set_password"):
        user.set_password(password)
    else:  # fallback if model lacks helper
        user.password_hash = generate_password_hash(password)

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
    payload = parse_json_request(request)
    email = _normalize_email(payload.get("email"))
    password = (payload.get("password") or "").strip()

    if not email or not password:
        raise BadRequest("Email and password are required.")

    # Case-insensitive lookup
    user = User.query.filter(func.lower(User.email) == email).first()
    if user is None:
        raise Unauthorized("Invalid email or password.")

    valid = False
    if hasattr(user, "check_password"):
        valid = user.check_password(password)
    else:
        valid = check_password_hash(getattr(user, "password_hash", ""), password)

    if not valid:
        raise Unauthorized("Invalid email or password.")

    token = create_access_token(identity=user.id)
    return (
        jsonify(
            {
                "access_token": token,
                "user": {"id": user.id, "email": user.email, "role": user.role},
            }
        ),
        HTTPStatus.OK,
    )
