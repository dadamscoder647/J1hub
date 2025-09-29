"""Listing and application models."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, or_

from app import db

LISTING_CATEGORIES = ("jobs", "housing", "rides", "gigs")


class Listing(db.Model):
    """Represents a job, housing, ride, or gig listing."""

    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.Enum(*LISTING_CATEGORIES, name="listing_category_enum"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    company_name = db.Column(db.String(120), nullable=True)
    contact_method = db.Column(db.String(50), nullable=False)
    contact_value = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(120), nullable=True)
    pay_rate = db.Column(db.Numeric(10, 2), nullable=True)
    currency = db.Column(db.String(8), nullable=True)
    shift = db.Column(db.String(120), nullable=True)
    is_public = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    creator = db.relationship("User", backref=db.backref("listings", lazy="dynamic"))
    applications = db.relationship(
        "Application",
        back_populates="listing",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def to_dict(self, include_private: bool = False) -> dict:
        """Serialize the listing to a dictionary."""

        pay_rate = (
            float(self.pay_rate) if isinstance(self.pay_rate, Decimal) else self.pay_rate
        )
        data = {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "company_name": self.company_name,
            "contact_method": self.contact_method if include_private else None,
            "contact_value": self.contact_value if include_private else None,
            "city": self.city,
            "pay_rate": pay_rate,
            "currency": self.currency,
            "shift": self.shift,
            "is_public": self.is_public,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "applications_count": self.applications.count()
            if hasattr(self.applications, "count")
            else len(self.applications or []),
        }
        return data

    @staticmethod
    def active_filter(query):
        """Filter for active listings considering expiration."""

        now = datetime.utcnow()
        return query.filter(
            and_(
                Listing.is_active.is_(True),
                or_(Listing.expires_at.is_(None), Listing.expires_at >= now),
            )
        )


class Application(db.Model):
    """Represents a worker application to a listing."""

    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    listing = db.relationship("Listing", back_populates="applications")
    applicant = db.relationship(
        "User", backref=db.backref("applications", lazy="dynamic")
    )

    def to_dict(self) -> dict:
        """Serialize the application."""

        return {
            "id": self.id,
            "user_id": self.user_id,
            "listing_id": self.listing_id,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
