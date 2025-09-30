"""Tests covering authentication and verification flows."""

from __future__ import annotations

from io import BytesIO

import pytest
from flask.testing import FlaskClient

from models import db
from models.user import User


def _create_user(email: str, password: str, role: str = "worker", *, verified: bool = False) -> User:
    """Helper to create and persist a user."""

    user = User(email=email, role=role, is_verified=verified)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def _login(client: FlaskClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    payload = response.get_json()
    return payload["access_token"]


def test_login_returns_access_token(client: FlaskClient, db_session):
    """Users should receive a JWT when providing valid credentials."""

    _create_user("j1@example.com", "J1Pass123")

    response = client.post(
        "/auth/login",
        json={"email": "j1@example.com", "password": "J1Pass123"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert "access_token" in data
    assert data["user"]["email"] == "j1@example.com"
    assert data["user"]["role"] == "worker"


@pytest.mark.parametrize(
    "payload, status_code",
    [
        ({"email": "j1@example.com"}, 400),
        ({"password": "J1Pass123"}, 400),
        ({"email": "j1@example.com", "password": "wrong"}, 401),
    ],
)
def test_login_validation(client: FlaskClient, db_session, payload, status_code):
    """Login endpoint should validate request bodies and credentials."""

    _create_user("j1@example.com", "J1Pass123")

    response = client.post("/auth/login", json=payload)

    assert response.status_code == status_code


def test_admin_can_approve_worker_document(client: FlaskClient, db_session, app):
    """End-to-end test for worker upload and admin approval flow."""

    with app.app_context():
        worker = _create_user("worker@example.com", "WorkerPass123")
        worker_id = worker.id
        admin = _create_user(
            "admin@example.com", "AdminPass123", role="admin", verified=True
        )

    worker_token = _login(client, "worker@example.com", "WorkerPass123")

    response = client.post(
        "/verify/upload",
        data={
            "doc_type": "j1_visa",
            "file": (BytesIO(b"test file"), "visa.pdf"),
        },
        headers={"Authorization": f"Bearer {worker_token}"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    document = response.get_json()["document"]
    assert document["status"] == "pending"

    admin_token = _login(client, "admin@example.com", "AdminPass123")

    approve_response = client.post(
        f"/admin/verify/{document['id']}/approve",
        json={"notes": "looks valid"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert approve_response.status_code == 200
    updated = approve_response.get_json()["document"]
    assert updated["status"] == "approved"
    assert updated["notes"] == "looks valid"

    with app.app_context():
        refreshed_worker = User.query.get(worker_id)
        assert refreshed_worker.is_verified is True
