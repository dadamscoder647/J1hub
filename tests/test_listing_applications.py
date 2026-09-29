"""Tests for listing application submission behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


def test_unverified_worker_cannot_apply_to_public_listing(app, client):
    with app.app_context():
        worker = User(
            email="unverified-worker@example.com",
            password_hash="hash",
            role="worker",
        )
        employer = User(
            email="public-employer@example.com",
            password_hash="hash",
            role="employer",
        )
        db.session.add_all([worker, employer])
        db.session.flush()
        listing = Listing(
            category="job",
            title="Public role",
            description="Open to applicants",
            contact_method="email",
            contact_value="jobs@example.com",
            created_by=employer.id,
            is_active=True,
            is_public=True,
        )
        db.session.add(listing)
        db.session.commit()
        worker_id, listing_id = worker.id, listing.id

    response = client.post(
        f"/api/v1/listings/{listing_id}/apply",
        json={"message": "Interested"},
        headers=_auth_header(app, worker_id),
    )
    assert response.status_code == 403
    assert "Verification approval" in response.get_json()["detail"]


def test_worker_cannot_apply_to_expired_listing(app, client):
    with app.app_context():
        worker_id, listing_id = _seed_worker_and_listing()
        listing = Listing.query.get(listing_id)
        listing.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
        db.session.commit()

    response = client.post(
        f"/api/v1/listings/{listing_id}/apply",
        json={"message": "Interested"},
        headers=_auth_header(app, worker_id),
    )
    assert response.status_code == 400
    assert "expired" in response.get_json()["detail"]


def test_employer_only_sees_owned_listings(app, client):
    with app.app_context():
        employer = User(
            email="first-employer@example.com",
            password_hash="hash",
            role="employer",
        )
        second_employer = User(
            email="second-employer@example.com",
            password_hash="hash",
            role="employer",
        )
        db.session.add_all([employer, second_employer])
        db.session.flush()
        own_listing = Listing(
            category="job",
            title="My listing",
            description="Owned by the current employer",
            contact_method="email",
            contact_value="mine@example.com",
            created_by=employer.id,
        )
        second_listing = Listing(
            category="job",
            title="Other listing",
            description="Owned by another employer",
            contact_method="email",
            contact_value="other@example.com",
            created_by=second_employer.id,
        )
        db.session.add_all([own_listing, second_listing])
        db.session.commit()
        employer_id, listing_id = employer.id, own_listing.id

    response = client.get(
        "/api/v1/listings/mine",
        headers=_auth_header(app, employer_id),
    )
    assert response.status_code == 200
    assert response.get_json()["count"] == 1
    assert response.get_json()["results"][0]["id"] == listing_id
