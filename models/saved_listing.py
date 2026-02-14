"""Saved listing model."""

from datetime import datetime

from . import db


class SavedListing(db.Model):
    """Represents a worker's favorited listing."""

    __tablename__ = "saved_listings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "listing_id", name="uq_saved_listing"),)

    user = db.relationship("User", backref=db.backref("saved_listings", lazy="dynamic"))
    listing = db.relationship("Listing", backref=db.backref("saved_by", lazy="dynamic"))

    def to_dict(self) -> dict:
        """Serialize a saved listing."""

        return {
            "id": self.id,
            "user_id": self.user_id,
            "listing_id": self.listing_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
