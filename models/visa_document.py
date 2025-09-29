"""Visa document model."""

from datetime import datetime

from . import db


DOC_TYPES = ("passport", "j1_visa")
VISA_STATUSES = ("pending", "approved", "denied")


class VisaDocument(db.Model):
    """Stores uploaded visa documentation for verification."""

    __tablename__ = "visa_documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    doc_type = db.Column(db.Enum(*DOC_TYPES, name="visa_document_type"), nullable=False)
    file_url = db.Column(db.String(512), nullable=False)
    status = db.Column(
        db.Enum(*VISA_STATUSES, name="visa_document_status"),
        nullable=False,
        default="pending",
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship(
        "User", backref=db.backref("visa_documents", lazy="dynamic")
    )

    def to_dict(self) -> dict:
        """Serialize the document."""

        return {
            "id": self.id,
            "user_id": self.user_id,
            "doc_type": self.doc_type,
            "file_url": self.file_url,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
