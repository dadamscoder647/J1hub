"""Verification blueprint for visa document uploads and review."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Iterable

from flask import Blueprint, current_app, jsonify, request, send_file
from flask.typing import ResponseReturnValue
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from models import db
from models.user import User
from models.visa_document import VisaDocument
from storage.local_storage import LocalStorage
from utils.request_validation import parse_json_request

verify_bp = Blueprint("verify", __name__)

MAX_UPLOAD_SIZE_DEFAULT = 10 * 1024 * 1024  # 10 MB
ALLOWED_UPLOAD_RULES_DEFAULT: dict[str, set[str]] = {
    "pdf": {"application/pdf"},
    "png": {"image/png"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
}


_SIGNATURE_BYTES = {
    "pdf": b"%PDF-",
    "png": b"\x89PNG\r\n\x1a\n",
}


def _get_current_user() -> User | None:
    try:
        identity = get_jwt_identity()
    except RuntimeError:
        return None
    if identity is None:
        return None
    user_id = identity
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        pass
    return User.query.get(user_id)


def _require_user() -> User:
    user = _get_current_user()
    if user is None:
        raise NotFound("User not found.")
    return user


def _require_admin() -> User:
    user = _require_user()
    if user.role != "admin":
        raise Forbidden("Admin privileges required.")
    return user


def _parse_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _get_allowed_upload_rules() -> dict[str, set[str]]:
    configured = current_app.config.get("ALLOWED_UPLOAD_RULES")
    normalized: dict[str, set[str]] = {}

    if isinstance(configured, dict):
        for extension, mimes in configured.items():
            if not isinstance(extension, str):
                continue
            ext = extension.strip().lower().lstrip(".")
            if not ext:
                continue

            if isinstance(mimes, str):
                mime_values: Iterable[str] = [mimes]
            elif isinstance(mimes, Iterable):
                mime_values = mimes
            else:
                mime_values = []

            parsed = {
                mime.strip().lower()
                for mime in mime_values
                if isinstance(mime, str) and mime.strip()
            }
            if parsed:
                normalized[ext] = parsed

    if not normalized:
        return {ext: set(mimes) for ext, mimes in ALLOWED_UPLOAD_RULES_DEFAULT.items()}

    if "jpeg" in normalized and "jpg" not in normalized:
        normalized["jpg"] = set(normalized["jpeg"])
    if "jpg" in normalized and "jpeg" not in normalized:
        normalized["jpeg"] = set(normalized["jpg"])

    return normalized


def _sniff_mime(header: bytes) -> str | None:
    if header.startswith(_SIGNATURE_BYTES["pdf"]):
        return "application/pdf"
    if header.startswith(_SIGNATURE_BYTES["png"]):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return None


def _validate_document(file: FileStorage) -> str:
    if file.filename is None or file.filename.strip() == "":
        raise BadRequest("A document file is required.")

    if "." not in file.filename:
        raise BadRequest("File must include a valid extension.")

    allowed_rules = _get_allowed_upload_rules()
    extension = file.filename.rsplit(".", 1)[-1].lower()
    if extension not in allowed_rules:
        allowed = ", ".join(sorted(allowed_rules))
        raise BadRequest(f"File type not allowed. Allowed types: {allowed}.")

    max_size = int(current_app.config.get("MAX_UPLOAD_SIZE", MAX_UPLOAD_SIZE_DEFAULT))
    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > max_size:
        raise BadRequest("File exceeds the maximum upload size of 10MB.")

    header = file.stream.read(16)
    file.stream.seek(0)
    sniffed_mime = _sniff_mime(header)
    if sniffed_mime is None:
        raise BadRequest("Unsupported or suspicious file content.")

    allowed_mimes = allowed_rules[extension]
    if sniffed_mime not in allowed_mimes:
        raise BadRequest("File content does not match the file extension.")

    declared_mime = (file.mimetype or "").lower().strip()
    if declared_mime and declared_mime not in allowed_mimes:
        raise BadRequest("Uploaded MIME type does not match the file extension.")

    return sniffed_mime


def _build_unique_filename(original: str) -> str:
    suffix = Path(original).suffix
    if not suffix:
        suffix = ""
    return f"{uuid.uuid4().hex}{suffix}"


def _get_document_or_404(document_id: int) -> VisaDocument:
    document = VisaDocument.query.get(document_id)
    if document is None:
        raise NotFound("Document not found.")
    return document


def _update_user_status(user: User, status: str) -> None:
    user.verification_status = status
    user.is_verified = status == "approved"


@verify_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():
    """Upload a document for verification and create a pending record."""

    user = _require_user()

    file = request.files.get("document")
    if not isinstance(file, FileStorage):
        raise BadRequest("A document file is required.")

    sniffed_mime = _validate_document(file)

    waiver_value = _parse_bool(request.form.get("waiver"))
    if waiver_value is None:
        raise BadRequest("waiver must be provided as a boolean value.")

    storage = LocalStorage(current_app.config.get("UPLOAD_DIR"))
    stored_filename = _build_unique_filename(file.filename or "document")
    stored_path = storage.save(file, stored_filename)

    document = VisaDocument(
        user_id=user.id,
        filename=file.filename or stored_filename,
        file_path=stored_path,
        file_type=sniffed_mime,
        waiver_acknowledged=waiver_value,
        status="pending",
    )

    db.session.add(document)
    _update_user_status(user, "pending")
    db.session.commit()

    return jsonify({"id": document.id, "status": document.status}), 201


@verify_bp.route("/status", methods=["GET"])
@jwt_required()
def verification_status():
    """Return the verification status and latest document metadata."""

    user = _require_user()

    latest_document = (
        VisaDocument.query.filter_by(user_id=user.id)
        .order_by(VisaDocument.created_at.desc())
        .first()
    )

    return jsonify(
        {
            "verification_status": user.verification_status,
            "latest_document": latest_document.to_dict() if latest_document else None,
        }
    )


@verify_bp.route("/doc/<int:document_id>", methods=["GET"])
@jwt_required()
def download_document(document_id: int):
    """Allow an administrator to download a stored verification document."""

    _require_admin()
    document = _get_document_or_404(document_id)

    storage = LocalStorage(current_app.config.get("UPLOAD_DIR"))
    if not storage.exists(document.file_path):
        raise NotFound("Stored file could not be found.")

    absolute_path = storage.base_directory / document.file_path
    return send_file(
        absolute_path,
        mimetype=document.file_type or "application/octet-stream",
        as_attachment=True,
        download_name=document.filename,
    )


def _serialize_pending_document(document: VisaDocument) -> dict[str, object]:
    return {
        "id": document.id,
        "user_id": document.user_id,
        "filename": document.filename,
        "created_at": document.created_at.isoformat() if document.created_at else None,
    }


def list_pending_documents() -> ResponseReturnValue:
    """Return a list of pending visa documents for admin review."""

    _require_admin()

    pending_documents = (
        VisaDocument.query.filter_by(status="pending")
        .order_by(VisaDocument.created_at.asc())
        .all()
    )

    return jsonify([_serialize_pending_document(document) for document in pending_documents])


@verify_bp.record_once
def _register_admin_routes(state) -> None:  # pragma: no cover - registration hook
    app = state.app
    app.add_url_rule(
        "/admin/verify/pending",
        view_func=jwt_required()(list_pending_documents),
        methods=["GET"],
        endpoint="verify.list_pending_documents",
    )


@verify_bp.route("/<int:document_id>/approve", methods=["POST"])
@jwt_required()
def approve_document(document_id: int):
    """Approve a document and mark the associated user as verified."""

    reviewer = _require_admin()
    document = _get_document_or_404(document_id)

    document.status = "approved"
    document.review_note = None
    document.reviewer_id = reviewer.id
    _update_user_status(document.user, "approved")

    db.session.commit()

    return jsonify(
        {
            "id": document.id,
            "status": document.status,
            "verification_status": document.user.verification_status,
        }
    )


@verify_bp.route("/<int:document_id>/reject", methods=["POST"])
@jwt_required()
def reject_document(document_id: int):
    """Reject a document, capturing an optional review note."""

    reviewer = _require_admin()
    document = _get_document_or_404(document_id)

    review_note = None
    if request.content_length and request.content_length > 0:
        if request.mimetype != "application/json":
            raise BadRequest("Review notes must be submitted as JSON.")
        payload = parse_json_request(request, allow_empty=True)
        review_note = payload.get("review_note") or payload.get("note")

    document.status = "rejected"
    document.review_note = review_note
    document.reviewer_id = reviewer.id
    _update_user_status(document.user, "rejected")

    db.session.commit()

    return jsonify(
        {
            "id": document.id,
            "status": document.status,
            "verification_status": document.user.verification_status,
            "review_note": document.review_note,
        }
    )
