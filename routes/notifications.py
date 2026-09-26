"""Notification endpoints."""

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.exceptions import NotFound

from models import db
from models.notification import Notification
from models.user import User

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("", methods=["GET"])
@jwt_required()
def list_notifications():
    """List notifications for the authenticated user."""

    user = User.query.get(get_jwt_identity())
    if user is None:
        raise NotFound("User not found.")

    items = (
        Notification.query.filter_by(user_id=user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return jsonify({"results": [item.to_dict() for item in items], "count": len(items)})


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
