"""Endpoints for visa document verification."""

from __future__ import annotations

from flask import Blueprint, abort, current_app, request

from app import db
from models import User, VisaDocument
from models.visa_document import DOCUMENT_STATUS, DOCUMENT_TYPES
from storage.local_storage import LocalStorage

verify_bp = Blueprint("verify", __name__, url_prefix="/verify")


def _get_document_or_404(document_id: int) -> VisaDocument:
    document = db.session.get(VisaDocument, document_id)
    if document is None:
        abort(404, description="Visa document not found.")
    return document


@verify_bp.route("/documents", methods=["POST"])
def upload_document() -> tuple[dict, int]:
    """Upload a new visa document for verification."""

    form = request.form
    user_id = form.get("user_id", type=int)
    doc_type = form.get("doc_type")
    notes = form.get("notes")

    if user_id is None:
        abort(400, description="user_id is required.")
    if doc_type not in DOCUMENT_TYPES:
        allowed = ", ".join(DOCUMENT_TYPES)
        abort(400, description=f"doc_type must be one of: {allowed}.")

    user = db.session.get(User, user_id)
    if user is None:
        abort(404, description="User not found.")

    file_storage = request.files.get("file")
    if file_storage is None or not getattr(file_storage, "filename", None):
        abort(400, description="A file must be provided.")

    storage = LocalStorage(current_app.config.get("UPLOAD_FOLDER"))
    stored_name = storage.save(file_storage, file_storage.filename)
    file_url = storage.url(stored_name)

    document = VisaDocument(
        user_id=user.id,
        doc_type=doc_type,
        file_url=file_url,
        notes=notes,
    )
    db.session.add(document)
    db.session.commit()

    return {"document": document.to_dict()}, 201


@verify_bp.route("/documents", methods=["GET"])
def list_documents() -> dict:
    """List visa documents filtered by optional user or status."""

    query = VisaDocument.query
    user_id = request.args.get("user_id", type=int)
    status = request.args.get("status")

    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    if status is not None:
        if status not in DOCUMENT_STATUS:
            allowed = ", ".join(DOCUMENT_STATUS)
            abort(400, description=f"status must be one of: {allowed}.")
        query = query.filter_by(status=status)

    documents = query.order_by(VisaDocument.created_at.desc()).all()
    return {"documents": [doc.to_dict() for doc in documents]}


@verify_bp.route("/documents/<int:document_id>", methods=["GET"])
def get_document(document_id: int) -> dict:
    """Return a single visa document by id."""

    document = _get_document_or_404(document_id)
    return {"document": document.to_dict()}


@verify_bp.route("/documents/<int:document_id>", methods=["PATCH"])
def update_document(document_id: int) -> dict:
    """Update the status or notes of a visa document."""

    document = _get_document_or_404(document_id)
    payload = request.get_json(silent=True) or {}

    status = payload.get("status")
    notes = payload.get("notes")

    if status is not None:
        if status not in DOCUMENT_STATUS:
            allowed = ", ".join(DOCUMENT_STATUS)
            abort(400, description=f"status must be one of: {allowed}.")
        document.status = status
        if status == "approved":
            document.user.is_verified = True
        elif status == "denied":
            document.user.is_verified = False
        elif status == "pending":
            document.user.is_verified = False

    if notes is not None:
        document.notes = notes

    db.session.commit()
    return {"document": document.to_dict()}
