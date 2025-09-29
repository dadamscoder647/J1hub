"""Listing model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, or_

from . import db

LISTING_CATEGORIES = ("job", "housing", "ride", "gig")
CONTACT_METHODS = ("phone", "email", "in_app")


class Listing(db.Model):
    """Represents a listing for jobs, housing, rides, or gigs."""

    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.Enum(*LISTING_CATEGORIES, name="listing_category"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    company_name = db.Column(db.String(255), nullable=True)
    contact_method = db.Column(
        db.Enum(*CONTACT_METHODS, name="listing_contact_method"), nullable=False
    )
    contact_value = db.Column(db.String(255), nullable=False)
    location_city = db.Column(db.String(120), nullable=True)
    pay_rate = db.Column(db.Numeric(10, 2), nullable=True)
    currency = db.Column(db.String(16), nullable=True)
    shift = db.Column(db.String(120), nullable=True)
    is_public = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    creator = db.relationship("User", backref=db.backref("listings", lazy="dynamic"))

    def to_dict(self, include_contact: bool = False) -> dict:
        """Serialize the listing."""

        pay_rate = (
            float(self.pay_rate) if isinstance(self.pay_rate, Decimal) else self.pay_rate
        )
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "company_name": self.company_name,
            "contact_method": self.contact_method if include_contact else None,
            "contact_value": self.contact_value if include_contact else None,
            "location_city": self.location_city,
            "pay_rate": pay_rate,
            "currency": self.currency,
            "shift": self.shift,
            "is_public": self.is_public,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def active_filter(query):
        """Filter a SQLAlchemy query for active listings."""

        now = datetime.utcnow()
        return query.filter(
            and_(
                Listing.is_active.is_(True),
                or_(Listing.expires_at.is_(None), Listing.expires_at >= now),
            )
        )
