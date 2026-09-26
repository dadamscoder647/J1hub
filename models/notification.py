"""Notification model."""

from datetime import datetime

from . import db

NOTIFICATION_EVENT_TYPES = (
    "verification_result",
    "application_update",
    "billing_credit_change",
)


class Notification(db.Model):
    """Represents an in-app notification."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_type = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.Text, nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("notifications", lazy="dynamic"))

    def to_dict(self) -> dict:
        """Serialize a notification."""

        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "title": self.title,
            "message": self.message,
            "metadata": self.metadata_json,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
