"""Authentication blueprint providing register and login endpoints."""

from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash

from models import db
from models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register() -> tuple:
    """Register a new user with an email, password, and optional role."""

    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    default_role = getattr(User.role.default, "arg", "worker")
    provided_role = payload.get("role")
    role = (provided_role if provided_role not in (None, "") else default_role) or default_role
    role = str(role).strip() or default_role

    if not email or not password:
        return (
            jsonify({"error": "Email and password are required."}),
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
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        return (
            jsonify({"error": "Email and password are required."}),
            HTTPStatus.BAD_REQUEST,
        )

    user = User.query.filter_by(email=email).first()
    if user is None or not check_password_hash(user.password_hash, password):
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
