"""Application model."""

from datetime import datetime

from . import db


class Application(db.Model):
    """Represents a worker application for a listing."""

    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    applicant = db.relationship(
        "User", backref=db.backref("applications", lazy="dynamic")
    )
    listing = db.relationship(
        "Listing", backref=db.backref("applications", lazy="dynamic")
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
