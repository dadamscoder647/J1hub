"""Authentication blueprint providing register and login endpoints."""

from datetime import datetime
from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.exceptions import BadRequest, Conflict, NotFound, Unauthorized

from models import db
from models.user import User
from utils.request_validation import parse_json_request

ALLOWED_ROLES = {"worker", "employer", "admin"}
WORKER_PROFILE_FIELDS = {"skills", "nationality", "visa_type", "visa_expiry", "availability"}
EMPLOYER_PROFILE_FIELDS = {
    "company_name",
    "company_website",
    "company_size",
    "company_industry",
}

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


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "skills": user.skills,
        "nationality": user.nationality,
        "visa_type": user.visa_type,
        "visa_expiry": user.visa_expiry.isoformat() if user.visa_expiry else None,
        "availability": user.availability,
        "company_name": user.company_name,
        "company_website": user.company_website,
        "company_size": user.company_size,
        "company_industry": user.company_industry,
    }


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

    if User.query.filter_by(email=email).first() is not None:
        raise Conflict("A user with that email already exists.")

    user = User(email=email, role=role)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "User registered successfully.",
                "user": _serialize_user(user),
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

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        raise Unauthorized("Invalid email or password.")

    access_token = create_access_token(identity=user.id)

    return (
        jsonify(
            {
                "access_token": access_token,
                "user": _serialize_user(user),
            }
        ),
        HTTPStatus.OK,
    )


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me() -> tuple:
    """Return the current user profile."""

    user = User.query.get(get_jwt_identity())
    if user is None:
        raise NotFound("User not found.")
    return jsonify({"user": _serialize_user(user)}), HTTPStatus.OK


@auth_bp.route("/me", methods=["PATCH"])
@jwt_required()
def update_profile() -> tuple:
    """Update worker/employer profile fields."""

    user = User.query.get(get_jwt_identity())
    if user is None:
        raise NotFound("User not found.")

    payload = parse_json_request(request, allow_empty=False)

    allowed_fields = set()
    if user.role == "worker":
        allowed_fields = WORKER_PROFILE_FIELDS
    elif user.role == "employer":
        allowed_fields = EMPLOYER_PROFILE_FIELDS
    elif user.role == "admin":
        allowed_fields = WORKER_PROFILE_FIELDS | EMPLOYER_PROFILE_FIELDS

    for key, value in payload.items():
        if key not in allowed_fields:
            continue
        if key == "visa_expiry" and value:
            try:
                value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError as exc:
                raise BadRequest("visa_expiry must be ISO 8601 format") from exc
        setattr(user, key, value)

    db.session.commit()
    return jsonify({"user": _serialize_user(user)}), HTTPStatus.OK
