"""VisaDocument model definition."""

from datetime import datetime

from . import db


VISA_DOCUMENT_STATUSES = ("pending", "approved", "rejected")


class VisaDocument(db.Model):
    """Represents an uploaded visa document awaiting review."""

    __tablename__ = "visa_documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(128), nullable=False)
    status = db.Column(
        db.Enum(*VISA_DOCUMENT_STATUSES, name="visa_document_status"),
        nullable=False,
        default="pending",
        server_default=db.text("'pending'"),
    )
    reviewer_id = db.Column(db.Integer, nullable=True)
    review_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=db.func.now(),
    )

    user = db.relationship(
        "User",
        backref=db.backref("visa_documents", lazy="dynamic"),
    )

    def __repr__(self) -> str:
        return (
            f"<VisaDocument id={self.id} user_id={self.user_id} status={self.status}>"
        )

    def to_dict(self) -> dict:
        """Serialize the visa document into a dictionary."""

        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "status": self.status,
            "reviewer_id": self.reviewer_id,
            "review_note": self.review_note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
