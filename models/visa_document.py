from datetime import datetime

from sqlalchemy.orm import validates

from . import db

DOC_TYPES = ("passport", "j1_visa")
STATUSES = ("pending", "approved", "denied")


class VisaDocument(db.Model):
    __tablename__ = "visa_documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    doc_type = db.Column(db.Enum(*DOC_TYPES, name="visa_document_types"), nullable=False)
    file_url = db.Column(db.String(512), nullable=False)
    status = db.Column(
        db.Enum(*STATUSES, name="visa_document_status"),
        nullable=False,
        default="pending",
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="documents")

    @validates("doc_type")
    def validate_doc_type(self, key, value):
        if value not in DOC_TYPES:
            raise ValueError("Invalid document type")
        return value

    @validates("status")
    def validate_status(self, key, value):
        if value not in STATUSES:
            raise ValueError("Invalid status")
        return value

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<VisaDocument {self.doc_type} ({self.status})>"
