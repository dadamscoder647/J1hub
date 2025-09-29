"""Visa document model definitions."""

from datetime import datetime

from app import db

DOCUMENT_TYPES = ("passport", "j1_visa")
DOCUMENT_STATUS = ("pending", "approved", "denied")


class VisaDocument(db.Model):
    """Stores uploaded visa documentation for verification."""

    __tablename__ = "visa_documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    doc_type = db.Column(db.Enum(*DOCUMENT_TYPES, name="doc_type_enum"), nullable=False)
    file_url = db.Column(db.String(256), nullable=False)
    status = db.Column(
        db.Enum(*DOCUMENT_STATUS, name="status_enum"),
        default="pending",
        nullable=False,
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="visa_documents")

    def to_dict(self) -> dict:
        """Serialize the document for API responses."""

        return {
            "id": self.id,
            "user_id": self.user_id,
            "doc_type": self.doc_type,
            "file_url": self.file_url,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<VisaDocument {self.id} user={self.user_id} type={self.doc_type}>"
