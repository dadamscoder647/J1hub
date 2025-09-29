"""Visa verification routes."""

from __future__ import annotations

import os
from typing import Tuple

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from models import db
from models.user import User
from models.visa_document import DOC_TYPES, VISA_STATUSES, VisaDocument
from storage.local_storage import LocalStorage

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
        return jsonify({"error": "User not found."}), 404

    file = request.files.get("file")
    if file is None or file.filename == "":
        return jsonify({"error": "A file is required."}), 400

    if not _allowed_file(file.filename):
        return jsonify({"error": "File type not allowed."}), 400

    doc_type = request.form.get("doc_type", "passport").lower()
    if doc_type not in DOC_TYPES:
        return jsonify({"error": "doc_type must be passport or j1_visa."}), 400

    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({"error": "File exceeds 10MB limit."}), 400

    storage = LocalStorage(current_app.config["UPLOAD_DIR"])
    saved_path = storage.save(file, file.filename)

    document = VisaDocument(
        user_id=user.id,
        doc_type=doc_type,
        file_url=saved_path,
        status="pending",
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
        return jsonify({"error": "User not found."}), 404

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


def _require_admin() -> Tuple[User, None] | Tuple[None, Tuple[str, int]]:
    user = _get_current_user()
    if user is None:
        return None, ("User not found.", 404)
    if user.role != "admin":
        return None, ("Admin privileges required.", 403)
    return user, None


@admin_bp.route("/verify/pending", methods=["GET"])
@jwt_required()
def admin_pending():
    user, error = _require_admin()
    if error:
        message, status_code = error
        return jsonify({"error": message}), status_code

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


def _update_document_status(document_id: int, status: str):
    if status not in VISA_STATUSES:
        return None, ("Invalid status.", 400)

    document = VisaDocument.query.get(document_id)
    if document is None:
        return None, ("Document not found.", 404)

    payload = request.get_json() or {}
    notes = payload.get("notes")

    document.status = status
    document.notes = notes

    if status == "approved":
        document.user.is_verified = True
    elif status == "denied":
        document.user.is_verified = False

    db.session.commit()
    return document, None


@admin_bp.route("/verify/<int:document_id>/approve", methods=["POST"])
@jwt_required()
def admin_approve(document_id: int):
    _, error = _require_admin()
    if error:
        message, status_code = error
        return jsonify({"error": message}), status_code

    document, doc_error = _update_document_status(document_id, "approved")
    if doc_error:
        message, status_code = doc_error
        return jsonify({"error": message}), status_code

    return jsonify({"document": document.to_dict()}), 200


@admin_bp.route("/verify/<int:document_id>/deny", methods=["POST"])
@jwt_required()
def admin_deny(document_id: int):
    _, error = _require_admin()
    if error:
        message, status_code = error
        return jsonify({"error": message}), status_code

    document, doc_error = _update_document_status(document_id, "denied")
    if doc_error:
        message, status_code = doc_error
        return jsonify({"error": message}), status_code

    return jsonify({"document": document.to_dict()}), 200
