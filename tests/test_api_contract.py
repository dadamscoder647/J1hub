"""API contract tests covering versioning and response schemas."""

from __future__ import annotations

from io import BytesIO

from flask_jwt_extended import create_access_token
from jsonschema import validate

from models import db
from models.listing import Listing
from models.user import User

ERROR_SCHEMA = {
    "type": "object",
    "required": ["error", "detail", "request_id"],
    "properties": {
        "error": {"type": "string"},
        "detail": {"type": "string"},
        "request_id": {"type": "string"},
    },
}

AUTH_SCHEMA = {
    "type": "object",
    "required": ["access_token", "user"],
    "properties": {
        "access_token": {"type": "string"},
        "user": {
            "type": "object",
            "required": ["id", "email", "role"],
            "properties": {
                "id": {"type": "integer"},
                "email": {"type": "string"},
                "role": {"type": "string"},
            },
        },
    },
}

LISTING_SEARCH_SCHEMA = {
    "type": "object",
    "required": ["results", "count"],
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "id",
                    "category",
                    "title",
                    "description",
                    "is_public",
                    "is_active",
                    "created_by",
                ],
            },
        },
        "count": {"type": "integer"},
    },
}

VERIFY_STATUS_SCHEMA = {
    "type": "object",
    "required": ["verification_status", "latest_document"],
    "properties": {
        "verification_status": {
            "type": "string",
            "enum": ["unverified", "pending", "approved", "rejected"],
        },
        "latest_document": {
            "anyOf": [
                {"type": "null"},
                {
                    "type": "object",
                    "required": [
                        "id",
                        "user_id",
                        "filename",
                        "file_path",
                        "file_type",
                        "status",
                        "waiver_acknowledged",
                    ],
                },
            ]
        },
    },
}


def _auth_header(app, user_id: int) -> dict[str, str]:
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def test_api_v1_prefix_works_for_auth_and_health(client):
    health = client.get("/api/v1/health")
    assert health.status_code == 200

    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "v1.user@example.com", "password": "testpass123"},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "v1.user@example.com", "password": "testpass123"},
    )
    assert login_response.status_code == 200
    validate(instance=login_response.get_json(), schema=AUTH_SCHEMA)


def test_error_schema_validation(client):
    response = client.post(
        "/api/v1/auth/register",
        data="not-json",
        content_type="text/plain",
    )

    assert response.status_code == 400
    validate(instance=response.get_json(), schema=ERROR_SCHEMA)


def test_listing_and_verification_schema_validation(app, client):
    with app.app_context():
        employer = User(email="employer@example.com", role="employer")
        employer.set_password("pass12345")
        worker = User(email="worker@example.com", role="worker")
        worker.set_password("pass12345")
        db.session.add_all([employer, worker])
        db.session.commit()

        listing = Listing(
            category="job",
            title="Server",
            description="Weekend shift",
            contact_method="email",
            contact_value="jobs@example.com",
            is_public=True,
            is_active=True,
            created_by=employer.id,
        )
        db.session.add(listing)
        db.session.commit()

        worker_id = worker.id

    listing_response = client.get("/api/v1/listings")
    assert listing_response.status_code == 200
    validate(instance=listing_response.get_json(), schema=LISTING_SEARCH_SCHEMA)

    verification_response = client.get(
        "/api/v1/verify/status",
        headers=_auth_header(app, worker_id),
    )
    assert verification_response.status_code == 200
    validate(instance=verification_response.get_json(), schema=VERIFY_STATUS_SCHEMA)


def test_pending_documents_schema_validation(app, client):
    with app.app_context():
        worker = User(email="verify.worker@example.com", role="worker")
        worker.set_password("workerpass")
        admin = User(email="verify.admin@example.com", role="admin")
        admin.set_password("adminpass")
        db.session.add_all([worker, admin])
        db.session.commit()

        worker_id = worker.id
        admin_id = admin.id

    upload_response = client.post(
        "/api/v1/verify/upload",
        data={
            "waiver": "true",
            "document": (BytesIO(b"pdf"), "test.pdf", "application/pdf"),
        },
        headers=_auth_header(app, worker_id),
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 201

    pending_response = client.get(
        "/admin/verify/pending",
        headers=_auth_header(app, admin_id),
    )
    assert pending_response.status_code == 200

    pending_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["id", "user_id", "filename", "created_at"],
            "properties": {
                "id": {"type": "integer"},
                "user_id": {"type": "integer"},
                "filename": {"type": "string"},
                "created_at": {"type": ["string", "null"]},
            },
        },
    }
    validate(instance=pending_response.get_json(), schema=pending_schema)
