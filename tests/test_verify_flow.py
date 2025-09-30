"""End-to-end verification flow tests."""

from __future__ import annotations

from io import BytesIO

from flask import Flask
from flask_jwt_extended import create_access_token

from models import db
from models.user import User
from models.visa_document import VisaDocument


def _register_and_login(
    app: Flask, client, email: str, password: str, role: str = "worker"
) -> tuple[int, str]:
    """Register a user and return their ID along with an access token."""

    register_payload = {"email": email, "password": password}
    if role != "worker":
        register_payload["role"] = role

    register_response = client.post("/auth/register", json=register_payload)
    assert register_response.status_code in {200, 201}

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    login_payload = login_response.get_json()
    user_id = login_payload["user"]["id"]

    with app.app_context():
        token = create_access_token(identity=str(user_id))

    return user_id, token


def test_upload_requires_jwt(client):
    """Uploading without a JWT should fail with 401."""

    response = client.post(
        "/verify/upload",
        data={
            "document": (BytesIO(b"dummy"), "test.pdf"),
            "waiver": "true",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 401


def test_upload_and_status(app: Flask, client):
    """Workers can upload documents and see pending status."""

    user_id, token = _register_and_login(
        app, client, "worker-flow@example.com", "secret123"
    )
    headers = {"Authorization": f"Bearer {token}"}

    upload_response = client.post(
        "/verify/upload",
        data={
            "document": (BytesIO(b"PDF data"), "document.pdf"),
            "waiver": "true",
        },
        headers=headers,
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201
    upload_payload = upload_response.get_json()
    assert upload_payload["status"] == "pending"

    status_response = client.get("/verify/status", headers=headers)
    assert status_response.status_code == 200
    status_payload = status_response.get_json()
    assert status_payload["verification_status"] == "pending"
    latest = status_payload["latest_document"]
    assert latest["status"] == "pending"
    assert latest["filename"] == "document.pdf"

    with app.app_context():
        refreshed_user = User.query.get(user_id)
    assert refreshed_user.verification_status == "pending"


def test_admin_approve(app: Flask, client):
    """Admins can approve documents via the review endpoint."""

    admin_id, admin_token = _register_and_login(
        app, client, "admin-flow@example.com", "adminpass", role="admin"
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    with app.app_context():
        worker = User(email="worker-approve@example.com", role="worker")
        worker.set_password("password")
        db.session.add(worker)
        db.session.commit()

        document = VisaDocument(
            user_id=worker.id,
            filename="pending.pdf",
            file_path="pending.pdf",
            file_type="application/pdf",
            status="pending",
            waiver_acknowledged=True,
        )
        db.session.add(document)
        db.session.commit()
        document_id = document.id
        worker_id = worker.id

    response = client.post(f"/verify/{document_id}/approve", headers=headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "approved"
    assert payload["verification_status"] == "approved"

    with app.app_context():
        refreshed_document = VisaDocument.query.get(document_id)
        refreshed_worker = User.query.get(worker_id)

    assert refreshed_document.status == "approved"
    assert refreshed_document.reviewer_id == admin_id
    assert refreshed_worker.verification_status == "approved"
    assert refreshed_worker.is_verified is True


def test_admin_reject_with_note(app: Flask, client):
    """Admins can reject documents and persist the review note."""

    _, admin_token = _register_and_login(
        app, client, "admin-reject@example.com", "adminpass", role="admin"
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    with app.app_context():
        worker = User(email="worker-reject@example.com", role="worker")
        worker.set_password("password")
        db.session.add(worker)
        db.session.commit()

        document = VisaDocument(
            user_id=worker.id,
            filename="to-review.pdf",
            file_path="to-review.pdf",
            file_type="application/pdf",
            status="pending",
            waiver_acknowledged=True,
        )
        db.session.add(document)
        db.session.commit()
        document_id = document.id
        worker_id = worker.id

    response = client.post(
        f"/verify/{document_id}/reject",
        json={"review_note": "Missing page 2"},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "rejected"
    assert payload["review_note"] == "Missing page 2"
    assert payload["verification_status"] == "rejected"

    with app.app_context():
        refreshed_document = VisaDocument.query.get(document_id)
        refreshed_worker = User.query.get(worker_id)

    assert refreshed_document.status == "rejected"
    assert refreshed_document.review_note == "Missing page 2"
    assert refreshed_worker.verification_status == "rejected"
    assert refreshed_worker.is_verified is False
