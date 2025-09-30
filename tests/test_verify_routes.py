"""Tests for verification upload and admin review routes."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from flask_jwt_extended import create_access_token

from models import db
from models.user import User
from models.visa_document import VisaDocument


def _auth_headers(app, user_id: int) -> dict[str, str]:
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def _create_user(email: str, role: str = "worker") -> User:
    user = User(email=email, password_hash="hash", role=role)
    db.session.add(user)
    db.session.commit()
    return user


def test_upload_document_creates_pending_record(app, client):
    """Uploading a document stores the file and marks the user pending."""

    with app.app_context():
        user = _create_user("worker@example.com")
        user_id = user.id

    data = {
        "document": (BytesIO(b"PDF data"), "visa.pdf"),
        "waiver": "true",
    }

    response = client.post(
        "/verify/upload",
        data=data,
        headers=_auth_headers(app, user_id),
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["status"] == "pending"

    with app.app_context():
        refreshed_user = User.query.get(user_id)
        document = VisaDocument.query.get(payload["id"])

    assert refreshed_user.verification_status == "pending"
    assert refreshed_user.is_verified is False
    assert document is not None
    assert document.waiver_acknowledged is True
    stored_file = Path(app.config["UPLOAD_DIR"]) / document.file_path
    assert stored_file.exists()


def test_status_endpoint_returns_latest_document(app, client):
    """Status endpoint includes user status and latest document metadata."""

    with app.app_context():
        user = _create_user("status@example.com")
        first = VisaDocument(
            user_id=user.id,
            filename="first.pdf",
            file_path="first.pdf",
            file_type="application/pdf",
            status="pending",
            waiver_acknowledged=True,
        )
        db.session.add(first)
        db.session.commit()

        second = VisaDocument(
            user_id=user.id,
            filename="second.pdf",
            file_path="second.pdf",
            file_type="application/pdf",
            status="approved",
            waiver_acknowledged=True,
        )
        user.verification_status = "approved"
        user.is_verified = True
        db.session.add(second)
        db.session.commit()
        user_id = user.id

    response = client.get(
        "/verify/status",
        headers=_auth_headers(app, user_id),
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["verification_status"] == "approved"
    assert payload["latest_document"]["filename"] == "second.pdf"


def test_admin_can_download_document(app, client):
    """Admins can download stored documents."""

    with app.app_context():
        admin = _create_user("admin@example.com", role="admin")
        admin.is_verified = True
        admin.verification_status = "approved"
        worker = _create_user("download@example.com")
        rel_path = "stored.pdf"
        stored = Path(app.config["UPLOAD_DIR"]) / rel_path
        stored.parent.mkdir(parents=True, exist_ok=True)
        stored.write_bytes(b"document-body")
        document = VisaDocument(
            user_id=worker.id,
            filename="stored.pdf",
            file_path=rel_path,
            file_type="application/pdf",
            status="pending",
            waiver_acknowledged=True,
        )
        db.session.add(document)
        db.session.commit()
        admin_id = admin.id
        document_id = document.id

    response = client.get(
        f"/verify/doc/{document_id}",
        headers=_auth_headers(app, admin_id),
    )
    assert response.status_code == 200
    assert response.data == b"document-body"


def test_admin_approve_updates_user_status(app, client):
    """Approving a document updates both the document and user status."""

    with app.app_context():
        admin = _create_user("approver@example.com", role="admin")
        admin.is_verified = True
        admin.verification_status = "approved"
        worker = _create_user("pending@example.com")
        document = VisaDocument(
            user_id=worker.id,
            filename="pending.pdf",
            file_path="pending.pdf",
            file_type="application/pdf",
            status="pending",
            waiver_acknowledged=False,
        )
        db.session.add(document)
        db.session.commit()
        admin_id = admin.id
        worker_id = worker.id
        document_id = document.id

    response = client.post(
        f"/verify/{document_id}/approve",
        headers=_auth_headers(app, admin_id),
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "approved"
    assert payload["verification_status"] == "approved"

    with app.app_context():
        refreshed_document = VisaDocument.query.get(document_id)
        refreshed_user = User.query.get(worker_id)
    assert refreshed_document.status == "approved"
    assert refreshed_document.reviewer_id == admin.id
    assert refreshed_user.is_verified is True
    assert refreshed_user.verification_status == "approved"


def test_admin_reject_updates_note_and_status(app, client):
    """Rejecting a document stores a note and marks the user rejected."""

    with app.app_context():
        admin = _create_user("rejector@example.com", role="admin")
        admin.is_verified = True
        admin.verification_status = "approved"
        worker = _create_user("reject@example.com")
        document = VisaDocument(
            user_id=worker.id,
            filename="reject.pdf",
            file_path="reject.pdf",
            file_type="application/pdf",
            status="pending",
            waiver_acknowledged=True,
        )
        db.session.add(document)
        db.session.commit()
        admin_id = admin.id
        worker_id = worker.id
        document_id = document.id

    response = client.post(
        f"/verify/{document_id}/reject",
        json={"review_note": "Missing signature"},
        headers=_auth_headers(app, admin_id),
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "rejected"
    assert payload["review_note"] == "Missing signature"

    with app.app_context():
        refreshed_document = VisaDocument.query.get(document_id)
        refreshed_user = User.query.get(worker_id)
    assert refreshed_document.status == "rejected"
    assert refreshed_document.review_note == "Missing signature"
    assert refreshed_document.reviewer_id == admin.id
    assert refreshed_user.verification_status == "rejected"
    assert refreshed_user.is_verified is False


def test_non_admin_cannot_access_admin_routes(app, client):
    """Workers cannot access admin-only verification routes."""

    with app.app_context():
        worker = _create_user("noadmin@example.com")
        document = VisaDocument(
            user_id=worker.id,
            filename="doc.pdf",
            file_path="doc.pdf",
            file_type="application/pdf",
            status="pending",
            waiver_acknowledged=False,
        )
        db.session.add(document)
        db.session.commit()
        worker_id = worker.id
        document_id = document.id

    response_doc = client.get(
        f"/verify/doc/{document_id}",
        headers=_auth_headers(app, worker_id),
    )
    response_approve = client.post(
        f"/verify/{document_id}/approve",
        headers=_auth_headers(app, worker_id),
    )
    response_reject = client.post(
        f"/verify/{document_id}/reject",
        headers=_auth_headers(app, worker_id),
    )

    assert response_doc.status_code == 403
    assert response_approve.status_code == 403
    assert response_reject.status_code == 403
