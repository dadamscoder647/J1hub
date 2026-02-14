"""Tests for listing application flow."""

from __future__ import annotations

from flask_jwt_extended import create_access_token

from models import db
from models.application import Application
from models.listing import Listing
from models.user import User


APPLY_PAYLOAD = {"message": "I am interested in this opportunity."}


def _auth_header(app, user_id: int) -> dict[str, str]:
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def _create_listing_with_worker() -> tuple[int, int]:
    employer = User(email="employer@app.test", password_hash="hash", role="employer")
    worker = User(
        email="worker@app.test",
        password_hash="hash",
        role="worker",
        is_verified=True,
        verification_status="approved",
    )
    db.session.add_all([employer, worker])
    db.session.flush()

    listing = Listing(
        category="job",
        title="Seasonal Role",
        description="Role details",
        contact_method="email",
        contact_value="employer@app.test",
        created_by=employer.id,
        is_public=True,
        is_active=True,
    )
    db.session.add(listing)
    db.session.commit()

    return listing.id, worker.id


def test_apply_to_listing_success(app, client):
    """Workers can apply once to an active listing."""

    with app.app_context():
        listing_id, worker_id = _create_listing_with_worker()

    response = client.post(
        f"/listings/{listing_id}/apply",
        json=APPLY_PAYLOAD,
        headers=_auth_header(app, worker_id),
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["listing_id"] == listing_id
    assert payload["user_id"] == worker_id

    with app.app_context():
        assert Application.query.filter_by(
            user_id=worker_id,
            listing_id=listing_id,
        ).count() == 1


def test_apply_to_listing_rejects_duplicate(app, client):
    """Duplicate applications return a conflict response."""

    with app.app_context():
        listing_id, worker_id = _create_listing_with_worker()

    first_response = client.post(
        f"/listings/{listing_id}/apply",
        json=APPLY_PAYLOAD,
        headers=_auth_header(app, worker_id),
    )
    assert first_response.status_code == 201

    duplicate_response = client.post(
        f"/listings/{listing_id}/apply",
        json=APPLY_PAYLOAD,
        headers=_auth_header(app, worker_id),
    )

    assert duplicate_response.status_code == 409
    duplicate_payload = duplicate_response.get_json()
    assert duplicate_payload["detail"] == "You have already applied to this listing."

    with app.app_context():
        assert Application.query.filter_by(
            user_id=worker_id,
            listing_id=listing_id,
        ).count() == 1
