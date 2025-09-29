from datetime import datetime
from app import db

class VisaDocument(db.Model):
    __tablename__ = "visa_documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    doc_type = db.Column(db.Enum("passport", "j1_visa", name="doc_type_enum"), nullable=False)
    file_url = db.Column(db.String(256), nullable=False)
    status = db.Column(db.Enum("pending", "approved", "denied", name="status_enum"), default="pending", nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("visa_documents", lazy=True))