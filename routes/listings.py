"""Listings blueprint with search, CRUD, and applications."""

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
from werkzeug.exceptions import BadRequest, Forbidden

from models import db
from models.application import Application
from models.employer_subscription import EmployerSubscription
from models.listing import CONTACT_METHODS, LISTING_CATEGORIES, Listing
from models.user import User
from utils.request_validation import parse_json_request

listings_bp = Blueprint("listings", __name__)


def _get_current_user(optional: bool = False) -> User | None:
    if optional:
        try:
            verify_jwt_in_request(optional=True)
        except Exception:  # pragma: no cover - defensive
            return None
    else:
        verify_jwt_in_request()

    try:
        identity = get_jwt_identity()
    except RuntimeError:
        return None
    if identity is None:
        return None
    return User.query.get(identity)


def _can_view_listing(listing: Listing, user: User | None) -> bool:
    if listing.is_public:
        return True
    if user is None:
        return False
    if user.role == "admin" or user.id == listing.created_by:
        return True
    return bool(user.is_verified)


def _can_view_contact(listing: Listing, user: User | None) -> bool:
    return _can_view_listing(listing, user)


def _can_modify_listing(listing: Listing, user: User | None) -> bool:
    if user is None:
        return False
    return user.role == "admin" or user.id == listing.created_by


def _parse_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "y"}:
        return True
    if lowered in {"0", "false", "no", "n"}:
        return False
    return None


@listings_bp.route("", methods=["GET"])
def search_listings():
    """Return listings with optional filters."""

    user = _get_current_user(optional=True)

    query = Listing.query

    category = request.args.get("category")
    if category:
        if category not in LISTING_CATEGORIES:
            raise BadRequest("Invalid category.")
        query = query.filter(Listing.category == category)

    search_term = request.args.get("q")
    if search_term:
        like = f"%{search_term.lower()}%"
        query = query.filter(
            or_(
                db.func.lower(Listing.title).like(like),
                db.func.lower(Listing.description).like(like),
                db.func.lower(Listing.company_name).like(like),
            )
        )

    city = request.args.get("city")
    if city:
        query = query.filter(
            db.func.lower(Listing.location_city).like(f"%{city.lower()}%")
        )

    active_param = request.args.get("active", "true")
    active = _parse_bool(active_param)
    if active is True:
        query = Listing.active_filter(query)
    elif active is False:
        now = datetime.utcnow()
        query = query.filter(
            or_(
                Listing.is_active.is_(False),
                and_(Listing.expires_at.isnot(None), Listing.expires_at < now),
            )
        )

    listings = query.order_by(Listing.created_at.desc()).all()

    payload = []
    for listing in listings:
        if not _can_view_listing(listing, user):
            continue
        payload.append(listing.to_dict(include_contact=_can_view_contact(listing, user)))

    return jsonify({"results": payload, "count": len(payload)})


def _validate_listing_payload(data: dict, partial: bool = False):
    errors = []

    required_fields = ["category", "title", "description", "contact_method", "contact_value"]
    if not partial:
        for field in required_fields:
            if not data.get(field):
                errors.append(f"{field} is required")

    category = data.get("category")
    if category and category not in LISTING_CATEGORIES:
        errors.append("category must be one of job, housing, ride, gig")

    contact_method = data.get("contact_method")
    if contact_method and contact_method not in CONTACT_METHODS:
        errors.append("contact_method must be one of phone, email, in_app")

    pay_rate = data.get("pay_rate")
    pay_rate_decimal = None
    if pay_rate not in (None, ""):
        try:
            pay_rate_decimal = Decimal(str(pay_rate))
        except (InvalidOperation, TypeError):
            errors.append("pay_rate must be numeric")

    expires_at = data.get("expires_at")
    expires_at_dt = None
    if expires_at:
        try:
            expires_at_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("expires_at must be ISO 8601 format")

    return errors, pay_rate_decimal, expires_at_dt


@listings_bp.route("", methods=["POST"])
@jwt_required()
def create_listing():
    """Create a listing. Employers and admins only."""

    user = _get_current_user()
    if user is None or user.role not in {"employer", "admin"}:
        raise Forbidden("Only employers or admins can create listings.")

    data = parse_json_request(request)
    errors, pay_rate, expires_at = _validate_listing_payload(data)
    if errors:
        raise BadRequest("; ".join(errors))

    subscription = None
    if user.role != "admin":
        subscription = EmployerSubscription.query.filter_by(user_id=user.id).first()
        now = datetime.utcnow()
        has_active_subscription = bool(
            subscription and subscription.has_active_subscription(now)
        )
        if not has_active_subscription:
            if not subscription or (subscription.listing_credits or 0) <= 0:
                return (
                    jsonify(
                        {
                            "error": (
                                "Listing credits or an active subscription is required "
                                "to post listings."
                            )
                        }
                    ),
                    402,
                )
            subscription.listing_credits -= 1

    listing = Listing(
        category=data.get("category"),
        title=data.get("title"),
        description=data.get("description"),
        company_name=data.get("company_name"),
        contact_method=data.get("contact_method"),
        contact_value=data.get("contact_value"),
        location_city=data.get("location_city"),
        pay_rate=pay_rate,
        currency=data.get("currency"),
        shift=data.get("shift"),
        is_public=_parse_bool(data.get("is_public"))
        if data.get("is_public") is not None
        else True,
        is_active=_parse_bool(data.get("is_active"))
        if data.get("is_active") is not None
        else True,
        expires_at=expires_at,
        created_by=user.id,
    )
    db.session.add(listing)
    if subscription is not None:
        db.session.add(subscription)
    db.session.commit()

    return jsonify(listing.to_dict(include_contact=True)), 201


@listings_bp.route("/<int:listing_id>", methods=["GET"])
def get_listing(listing_id: int):
    listing = Listing.query.get_or_404(listing_id)
    user = _get_current_user(optional=True)

    if not _can_view_listing(listing, user):
        raise Forbidden("Not authorized to view this listing.")

    include_contact = _can_view_contact(listing, user)
    return jsonify(listing.to_dict(include_contact=include_contact))


@listings_bp.route("/<int:listing_id>", methods=["PATCH"])
@jwt_required()
def update_listing(listing_id: int):
    listing = Listing.query.get_or_404(listing_id)
    user = _get_current_user()
    if not _can_modify_listing(listing, user):
        raise Forbidden("You do not have permission to update this listing.")

    data = parse_json_request(request, allow_empty=False)
    errors, pay_rate, expires_at = _validate_listing_payload(data, partial=True)
    if errors:
        raise BadRequest("; ".join(errors))

    for field in [
        "category",
        "title",
        "description",
        "company_name",
        "contact_method",
        "contact_value",
        "location_city",
        "currency",
        "shift",
    ]:
        if field in data and data[field] is not None:
            setattr(listing, field, data[field])

    if pay_rate is not None:
        listing.pay_rate = pay_rate
    if "pay_rate" in data and data.get("pay_rate") in (None, ""):
        listing.pay_rate = None

    if expires_at is not None:
        listing.expires_at = expires_at
    if "expires_at" in data and not data.get("expires_at"):
        listing.expires_at = None

    if "is_public" in data:
        parsed = _parse_bool(data.get("is_public"))
        if parsed is None:
            raise BadRequest("is_public must be boolean")
        listing.is_public = parsed

    if "is_active" in data:
        parsed = _parse_bool(data.get("is_active"))
        if parsed is None:
            raise BadRequest("is_active must be boolean")
        listing.is_active = parsed

    db.session.commit()
    include_contact = _can_view_contact(listing, user)
    return jsonify(listing.to_dict(include_contact=include_contact))


@listings_bp.route("/<int:listing_id>/apply", methods=["POST"])
@jwt_required()
def apply_to_listing(listing_id: int):
    listing = Listing.query.get_or_404(listing_id)
    user = _get_current_user()

    if user is None or user.role != "worker":
        raise Forbidden("Only workers can apply to listings.")

    if not _can_view_listing(listing, user):
        raise Forbidden("You must be verified to apply to this listing.")

    if not listing.is_active:
        raise BadRequest("Listing is not active.")

    data = parse_json_request(request)
    message = data.get("message")
    if not message:
        raise BadRequest("message is required")

    application = Application(user_id=user.id, listing_id=listing.id, message=message)
    db.session.add(application)
    db.session.commit()

    return jsonify(application.to_dict()), 201
