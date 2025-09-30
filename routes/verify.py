"""Visa verification routes."""

from __future__ import annotations

import os

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from models import db
from models.user import User
from models.visa_document import VISA_DOCUMENT_STATUSES, VisaDocument
from storage.local_storage import LocalStorage
from utils.request_validation import parse_json_request

verify_bp = Blueprint("verify", __name__)
admin_bp = Blueprint("admin_verify", __name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}


def _get_current_user() -> User | None:
    try:
        identity = get_jwt_identity()
    except RuntimeError:
        return None
    if identity is None:
        return None
    return User.query.get(identity)


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@verify_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():
    """Upload a visa document for verification."""

    user = _get_current_user()
    if user is None:
        raise NotFound("User not found.")

    file = request.files.get("file")
    if file is None or file.filename == "":
        raise BadRequest("A file is required.")

    if not _allowed_file(file.filename):
        raise BadRequest("File type not allowed.")

    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_FILE_SIZE:
        raise BadRequest("File exceeds 10MB limit.")

    storage = LocalStorage(current_app.config["UPLOAD_DIR"])
    saved_path = storage.save(file, file.filename)

    document = VisaDocument(
        user_id=user.id,
        filename=file.filename,
        file_path=saved_path,
        file_type=file.mimetype or "application/octet-stream",
    )
    db.session.add(document)
    db.session.commit()

    return jsonify({"document": document.to_dict()}), 201


@verify_bp.route("/status", methods=["GET"])
@jwt_required()
def verification_status():
    """Return the verification status for the current user."""

    user = _get_current_user()
    if user is None:
        raise NotFound("User not found.")

    latest_document = (
        VisaDocument.query.filter_by(user_id=user.id)
        .order_by(VisaDocument.created_at.desc())
        .first()
    )

    return jsonify(
        {
            "is_verified": user.is_verified,
            "latest_document": latest_document.to_dict() if latest_document else None,
        }
    )


def _require_admin() -> User:
    user = _get_current_user()
    if user is None:
        raise NotFound("User not found.")
    if user.role != "admin":
        raise Forbidden("Admin privileges required.")
    return user


@admin_bp.route("/verify/pending", methods=["GET"])
@jwt_required()
def admin_pending():
    _require_admin()

    pending_documents = (
        VisaDocument.query.filter_by(status="pending")
        .order_by(VisaDocument.created_at.asc())
        .all()
    )
    return jsonify(
        {
            "pending": [doc.to_dict() for doc in pending_documents],
            "count": len(pending_documents),
        }
    )


def _update_document_status(document_id: int, status: str) -> VisaDocument:
    if status not in VISA_DOCUMENT_STATUSES:
        raise BadRequest("Invalid status.")

    document = VisaDocument.query.get(document_id)
    if document is None:
        raise NotFound("Document not found.")

    payload = {}
    if request.content_length and request.content_length > 0:
        payload = parse_json_request(request, allow_empty=True)

    notes = None
    if isinstance(payload, dict):
        notes = payload.get("notes")

    document.status = status
    document.review_note = notes
    reviewer = _get_current_user()
    document.reviewer_id = reviewer.id if reviewer else None

    if status == "approved":
        document.user.is_verified = True
    elif status == "rejected":
        document.user.is_verified = False

    db.session.commit()
    return document


@admin_bp.route("/verify/<int:document_id>/approve", methods=["POST"])
@jwt_required()
def admin_approve(document_id: int):
    _require_admin()

    document = _update_document_status(document_id, "approved")

    return jsonify({"document": document.to_dict()}), 200


@admin_bp.route("/verify/<int:document_id>/deny", methods=["POST"])
@jwt_required()
def admin_deny(document_id: int):
    _require_admin()

    document = _update_document_status(document_id, "rejected")

    return jsonify({"document": document.to_dict()}), 200
