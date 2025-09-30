"""Employer subscription model for billing."""

from datetime import datetime

from . import db


class EmployerSubscription(db.Model):
    """Stores employer billing status including credits and subscriptions."""

    __tablename__ = "employer_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    active_until = db.Column(db.DateTime, nullable=True)
    listing_credits = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = db.relationship("User", back_populates="subscription")

    def has_active_subscription(self, now=None) -> bool:
        """Return True if the subscription is currently active."""

        if self.active_until is None:
            return False
        now = now or datetime.utcnow()
        return self.active_until >= now
