"""Listings blueprint with CRUD and application endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
)
from sqlalchemy import and_, or_

from app import db
from models.listing import Application, Listing, LISTING_CATEGORIES
from models.user import User

listings_bp = Blueprint("listings", __name__)


def _get_current_user(optional: bool = False) -> User | None:
    """Return the current user when a JWT is present."""

    if optional:
        try:
            verify_jwt_in_request(optional=True)
        except Exception:
            return None
    else:
        verify_jwt_in_request()

    identity = get_jwt_identity()
    if identity is None:
        return None
    return User.query.get(identity)


def _forbidden(message: str):
    return jsonify({"error": message}), 403


def _str_to_bool(value: str) -> bool | None:
    if value is None:
        return None
    value = value.lower()
    if value in {"1", "true", "yes", "y"}:
        return True
    if value in {"0", "false", "no", "n"}:
        return False
    return None


def _parse_iso_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError("Invalid ISO 8601 datetime") from exc


def _can_access_listing(listing: Listing, user: User | None) -> bool:
    if listing.is_public:
        return True
    if user is None:
        return False
    if user.role == "admin" or user.id == listing.created_by:
        return True
    return bool(user.is_verified)


def _visible_contact(listing: Listing, user: User | None) -> bool:
    return _can_access_listing(listing, user)


def _filter_visibility(query, user: User | None):
    if user is None:
        return query.filter(Listing.is_public.is_(True))
    if user.role == "admin":
        return query
    if user.is_verified:
        return query
    # Unverified users may only see public listings or ones they created.
    return query.filter(
        or_(
            Listing.is_public.is_(True),
            Listing.created_by == user.id,
        )
    )


@listings_bp.route("", methods=["GET"])
def list_listings():
    """Return listings with optional search filters."""

    current_user = _get_current_user(optional=True)
    query = Listing.query

    category = request.args.get("category")
    if category:
        if category not in LISTING_CATEGORIES:
            return jsonify({"error": "Invalid category."}), 400
        query = query.filter(Listing.category == category)

    search_term = request.args.get("q")
    if search_term:
        like_pattern = f"%{search_term.lower()}%"
        query = query.filter(
            or_(
                db.func.lower(Listing.title).like(like_pattern),
                db.func.lower(Listing.description).like(like_pattern),
                db.func.lower(Listing.company_name).like(like_pattern),
            )
        )

    city = request.args.get("city")
    if city:
        query = query.filter(db.func.lower(Listing.city).like(f"%{city.lower()}%"))

    active_filter = request.args.get("active")
    active_value = _str_to_bool(active_filter) if active_filter is not None else True
    if active_value is True:
        query = Listing.active_filter(query)
    elif active_value is False:
        now = datetime.utcnow()
        query = query.filter(
            or_(
                Listing.is_active.is_(False),
                and_(Listing.expires_at.isnot(None), Listing.expires_at < now),
            )
        )

    query = _filter_visibility(query, current_user)
    listings = query.order_by(Listing.created_at.desc()).all()

    payload = []
    for listing in listings:
        if not _can_access_listing(listing, current_user):
            # Filter out private listings if the user lacks verification.
            continue
        include_contact = _visible_contact(listing, current_user)
        payload.append(listing.to_dict(include_private=include_contact))

    return jsonify({"results": payload, "count": len(payload)})


@listings_bp.route("", methods=["POST"])
@jwt_required()
def create_listing():
    """Create a new listing (employers/admins only)."""

    current_user = _get_current_user()
    if current_user is None:
        return _forbidden("Authentication required.")
    if current_user.role not in {"employer", "admin"}:
        return _forbidden("Only employers or admins can create listings.")

    data = request.get_json() or {}

    errors = []
    for field in ("category", "title", "description", "contact_method", "contact_value"):
        if not data.get(field):
            errors.append(f"{field} is required")

    category = data.get("category")
    if category and category not in LISTING_CATEGORIES:
        errors.append("category must be one of jobs, housing, rides, gigs")

    pay_rate_value = data.get("pay_rate")
    pay_rate = None
    if pay_rate_value not in (None, ""):
        try:
            pay_rate = Decimal(str(pay_rate_value))
        except (InvalidOperation, TypeError):
            errors.append("pay_rate must be a valid number")

    expires_at_value = data.get("expires_at")
    expires_at = None
    if expires_at_value:
        try:
            expires_at = _parse_iso_datetime(expires_at_value)
        except ValueError:
            errors.append("expires_at must be ISO 8601 format")

    if errors:
        return jsonify({"errors": errors}), 400

    listing = Listing(
        category=category,
        title=data.get("title"),
        description=data.get("description"),
        company_name=data.get("company_name"),
        contact_method=data.get("contact_method"),
        contact_value=data.get("contact_value"),
        city=data.get("city"),
        pay_rate=pay_rate,
        currency=data.get("currency"),
        shift=data.get("shift"),
        is_public=bool(data.get("is_public", True)),
        is_active=bool(data.get("is_active", True)),
        expires_at=expires_at,
        created_by=current_user.id,
    )
    db.session.add(listing)
    db.session.commit()

    include_contact = _visible_contact(listing, current_user)
    return jsonify(listing.to_dict(include_private=include_contact)), 201


@listings_bp.route("/<int:listing_id>", methods=["GET"])
def get_listing(listing_id: int):
    """Retrieve a single listing."""

    listing = Listing.query.get_or_404(listing_id)
    current_user = _get_current_user(optional=True)
    if not _can_access_listing(listing, current_user):
        return _forbidden("Listing not available.")

    include_contact = _visible_contact(listing, current_user)
    return jsonify(listing.to_dict(include_private=include_contact))


@listings_bp.route("/<int:listing_id>", methods=["PATCH"])
@jwt_required()
def update_listing(listing_id: int):
    """Update a listing (owner or admin)."""

    listing = Listing.query.get_or_404(listing_id)
    current_user = _get_current_user()
    if current_user is None:
        return _forbidden("Authentication required.")
    if current_user.role != "admin" and listing.created_by != current_user.id:
        return _forbidden("Only the owner or an admin can update this listing.")

    data = request.get_json() or {}
    allowed_fields = {
        "category",
        "title",
        "description",
        "company_name",
        "contact_method",
        "contact_value",
        "city",
        "pay_rate",
        "currency",
        "shift",
        "is_public",
        "is_active",
        "expires_at",
    }

    errors = []

    for key in data:
        if key not in allowed_fields:
            errors.append(f"{key} is not an updatable field")
    if errors:
        return jsonify({"errors": errors}), 400

    if "category" in data:
        if data["category"] not in LISTING_CATEGORIES:
            errors.append("category must be one of jobs, housing, rides, gigs")
        else:
            listing.category = data["category"]

    for attr in ("title", "description", "company_name", "contact_method", "contact_value", "city", "currency", "shift"):
        if attr in data and data[attr] is not None:
            setattr(listing, attr, data[attr])

    if "is_public" in data:
        listing.is_public = bool(data["is_public"])
    if "is_active" in data:
        listing.is_active = bool(data["is_active"])

    if "pay_rate" in data:
        if data["pay_rate"] in (None, ""):
            listing.pay_rate = None
        else:
            try:
                listing.pay_rate = Decimal(str(data["pay_rate"]))
            except (InvalidOperation, TypeError):
                errors.append("pay_rate must be a valid number")

    if "expires_at" in data:
        if data["expires_at"] in (None, ""):
            listing.expires_at = None
        else:
            try:
                listing.expires_at = _parse_iso_datetime(data["expires_at"])
            except ValueError:
                errors.append("expires_at must be ISO 8601 format")

    if errors:
        return jsonify({"errors": errors}), 400

    db.session.commit()
    include_contact = _visible_contact(listing, current_user)
    return jsonify(listing.to_dict(include_private=include_contact))


@listings_bp.route("/<int:listing_id>/apply", methods=["POST"])
@jwt_required()
def apply_to_listing(listing_id: int):
    """Allow a worker to apply to a listing."""

    listing = Listing.query.get_or_404(listing_id)
    current_user = _get_current_user()
    if current_user is None:
        return _forbidden("Authentication required.")
    if current_user.role not in {"worker", "user"}:
        return _forbidden("Only workers can apply to listings.")
    if not _can_access_listing(listing, current_user):
        return _forbidden("You are not allowed to view this listing.")

    now = datetime.utcnow()
    if not listing.is_active or (listing.expires_at and listing.expires_at < now):
        return jsonify({"error": "This listing is not accepting applications."}), 400

    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    already_applied = Application.query.filter_by(
        user_id=current_user.id, listing_id=listing.id
    ).first()
    if already_applied:
        return jsonify({"error": "You have already applied to this listing."}), 400

    application = Application(
        user_id=current_user.id,
        listing_id=listing.id,
        message=message,
    )
    db.session.add(application)
    db.session.commit()

    return jsonify(application.to_dict()), 201
