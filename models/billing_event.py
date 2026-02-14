"""Billing event model for webhook-backed account history."""

from datetime import datetime

from . import db


class BillingEvent(db.Model):
    """Stores lightweight billing activity for account visibility."""

    __tablename__ = "billing_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    provider = db.Column(db.String(32), nullable=False, default="stripe")
    event_type = db.Column(db.String(128), nullable=False)
    provider_event_id = db.Column(db.String(128), nullable=True, unique=True)
    details = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User")

    def to_dict(self) -> dict:
        """Serialize billing event payload for API responses."""

        return {
            "id": self.id,
            "provider": self.provider,
            "event_type": self.event_type,
            "provider_event_id": self.provider_event_id,
            "details": self.details or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
