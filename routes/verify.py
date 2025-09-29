from http import HTTPStatus
from typing import Optional

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from models import db
from models.user import User
from models.visa_document import DOC_TYPES, STATUSES, VisaDocument
from storage.local_storage import LocalStorage

verify_bp = Blueprint("verify", __name__)
admin_bp = Blueprint("admin_verify", __name__)


def _get_storage() -> LocalStorage:
    upload_dir = current_app.config["UPLOAD_DIR"]
    return LocalStorage(upload_dir)


def _get_current_user() -> Optional[User]:
    identity = get_jwt_identity()
    if identity is None:
        return None
    return User.query.get(identity)


def _require_admin(user: Optional[User]) -> bool:
    return bool(user and user.role == "admin")


@verify_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():
    user = _get_current_user()
    if user is None:
        return jsonify({"message": "User not found"}), HTTPStatus.UNAUTHORIZED

    doc_type = request.form.get("doc_type")
    if doc_type not in DOC_TYPES:
        return jsonify({"message": "Invalid or missing document type."}), HTTPStatus.BAD_REQUEST

    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"message": "No file provided."}), HTTPStatus.BAD_REQUEST

    storage = _get_storage()
    try:
        file_url = storage.save(file, file.filename)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), HTTPStatus.BAD_REQUEST

    document = VisaDocument(user=user, doc_type=doc_type, file_url=file_url)
    db.session.add(document)
    db.session.commit()

    return (
        jsonify(
            {
                "id": document.id,
                "doc_type": document.doc_type,
                "status": document.status,
                "file_url": document.file_url,
                "created_at": document.created_at.isoformat(),
            }
        ),
        HTTPStatus.CREATED,
    )


@verify_bp.route("/status", methods=["GET"])
@jwt_required()
def list_documents():
    user = _get_current_user()
    if user is None:
        return jsonify({"message": "User not found"}), HTTPStatus.UNAUTHORIZED

    documents = (
        user.documents.order_by(VisaDocument.created_at.desc()).all()
        if hasattr(user.documents, "order_by")
        else user.documents  # type: ignore[assignment]
    )

    return jsonify(
        [
            {
                "id": doc.id,
                "doc_type": doc.doc_type,
                "status": doc.status,
                "file_url": doc.file_url,
                "notes": doc.notes,
                "created_at": doc.created_at.isoformat(),
            }
            for doc in documents
        ]
    )


def _update_document_status(document_id: int, status: str, notes: Optional[str]) -> VisaDocument:
    if status not in STATUSES:
        raise ValueError("Invalid status")

    document = VisaDocument.query.get_or_404(document_id)
    document.status = status
    if notes is not None:
        document.notes = notes

    if status == "approved" and document.doc_type == "j1_visa":
        document.user.is_verified = True
    elif status == "denied" and document.doc_type == "j1_visa":
        document.user.is_verified = False

    db.session.commit()
    return document


@admin_bp.route("/pending", methods=["GET"])
@jwt_required()
def list_pending_documents():
    user = _get_current_user()
    if not _require_admin(user):
        return jsonify({"message": "Admin privileges required"}), HTTPStatus.FORBIDDEN

    documents = (
        VisaDocument.query.filter_by(status="pending")
        .order_by(VisaDocument.created_at.asc())
        .all()
    )
    return jsonify(
        [
            {
                "id": doc.id,
                "user_id": doc.user_id,
                "doc_type": doc.doc_type,
                "status": doc.status,
                "file_url": doc.file_url,
                "created_at": doc.created_at.isoformat(),
            }
            for doc in documents
        ]
    )


@admin_bp.route("/<int:document_id>/approve", methods=["POST"])
@jwt_required()
def approve_document(document_id: int):
    user = _get_current_user()
    if not _require_admin(user):
        return jsonify({"message": "Admin privileges required"}), HTTPStatus.FORBIDDEN

    notes = request.json.get("notes") if request.is_json else None
    document = _update_document_status(document_id, "approved", notes)
    return jsonify({"id": document.id, "status": document.status, "notes": document.notes})


@admin_bp.route("/<int:document_id>/deny", methods=["POST"])
@jwt_required()
def deny_document(document_id: int):
    user = _get_current_user()
    if not _require_admin(user):
        return jsonify({"message": "Admin privileges required"}), HTTPStatus.FORBIDDEN

    notes = request.json.get("notes") if request.is_json else None
    document = _update_document_status(document_id, "denied", notes)
    return jsonify({"id": document.id, "status": document.status, "notes": document.notes})
