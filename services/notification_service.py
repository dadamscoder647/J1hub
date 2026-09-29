"""Notification helpers for domain events."""

from __future__ import annotations

import json

from models import db
from models.notification import NOTIFICATION_EVENT_TYPES, Notification


def create_notification(
    user_id: int,
    event_type: str,
    title: str,
    message: str,
    metadata: dict | None = None,
) -> Notification:
    """Persist an in-app notification for the target user."""

    if event_type not in NOTIFICATION_EVENT_TYPES:
        raise ValueError("Unsupported notification event type.")

    notification = Notification(
        user_id=user_id,
        event_type=event_type,
        title=title,
        message=message,
        metadata_json=json.dumps(metadata or {}),
    )
    db.session.add(notification)
    return notification
