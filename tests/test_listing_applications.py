"""Tests for listing application submission behavior."""

from __future__ import annotations

from flask_jwt_extended import create_access_token

from models import db
from models.application import Application
from models.listing import Listing
from models.user import User


def _auth_header(app, user_id: int) -> dict[str, str]:
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def _seed_worker_and_listing() -> tuple[int, int]:
    employer = User(
        email="employer-apps@example.com",
        password_hash="hash",
        role="employer",
        is_verified=True,
    )
    worker = User(
        email="worker-apps@example.com",
        password_hash="hash",
        role="worker",
        is_verified=True,
    )
    db.session.add_all([employer, worker])
    db.session.flush()

    listing = Listing(
        category="job",
        title="Line Cook",
        description="Kitchen role",
        contact_method="email",
        contact_value="jobs@example.com",
        created_by=employer.id,
        is_active=True,
        is_public=True,
    )
    db.session.add(listing)
    db.session.commit()

    return worker.id, listing.id


def test_apply_to_listing_returns_409_for_duplicate_application(app, client):
    """Applying twice to the same listing should return a conflict response."""

    with app.app_context():
        worker_id, listing_id = _seed_worker_and_listing()

    first_response = client.post(
        f"/listings/{listing_id}/apply",
        json={"message": "I am interested."},
        headers=_auth_header(app, worker_id),
    )
    assert first_response.status_code == 201

    duplicate_response = client.post(
        f"/listings/{listing_id}/apply",
        json={"message": "Applying again."},
        headers=_auth_header(app, worker_id),
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.get_json() == {
        "error": "You have already applied to this listing."
    }

    with app.app_context():
        assert (
            Application.query.filter_by(user_id=worker_id, listing_id=listing_id).count()
            == 1
        )
