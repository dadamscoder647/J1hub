"""Notification endpoints."""

from __future__ import annotations

from math import ceil

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.exceptions import BadRequest, NotFound

from models import db
from models.notification import Notification
from models.user import User

notifications_bp = Blueprint("notifications", __name__)
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


def _parse_pagination_params() -> tuple[int, int]:
    page_raw = request.args.get("page", str(DEFAULT_PAGE))
    per_page_raw = request.args.get("per_page", str(DEFAULT_PER_PAGE))

    try:
        page = int(page_raw)
        per_page = int(per_page_raw)
    except (TypeError, ValueError):
        raise BadRequest("page and per_page must be integers.") from None

    if page < 1:
        raise BadRequest("page must be greater than 0.")
    if per_page < 1:
        raise BadRequest("per_page must be greater than 0.")

    return page, min(per_page, MAX_PER_PAGE)


@notifications_bp.route("", methods=["GET"])
@jwt_required()
def list_notifications():
    """List notifications for the authenticated user."""

    user = User.query.get(get_jwt_identity())
    if user is None:
        raise NotFound("User not found.")

    page, per_page = _parse_pagination_params()
    query = Notification.query.filter_by(user_id=user.id)
    total = query.count()
    total_pages = ceil(total / per_page) if total else 0
    if page <= total_pages:
        items = (
            query.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
    else:
        items = []

    return jsonify(
        {
            "results": [item.to_dict() for item in items],
            "count": len(items),
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }
    )


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@jwt_required()
def mark_read(notification_id: int):
    """Mark a notification as read."""

    user = User.query.get(get_jwt_identity())
    if user is None:
        raise NotFound("User not found.")

    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != user.id:
        raise NotFound("Notification not found.")

    notification.is_read = True
    db.session.commit()
    return jsonify(notification.to_dict())
