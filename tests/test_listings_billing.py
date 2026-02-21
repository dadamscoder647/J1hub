"""Tests for listing creation billing enforcement."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flask_jwt_extended import create_access_token

from models import db
from models.employer_subscription import EmployerSubscription
from models.listing import Listing
from models.user import User


LISTING_PAYLOAD = {
    "category": "job",
    "title": "Test Role",
    "description": "Job description",
    "contact_method": "email",
    "contact_value": "employer@example.com",
}


def _create_employer(email: str = "credit@example.com") -> int:
    user = User(email=email, password_hash="hash", role="employer")
    db.session.add(user)
    db.session.commit()
    return user.id


def _auth_header(app, user_id: int) -> dict[str, str]:
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def test_listing_creation_requires_credits(app, client):
    """Employers without credits or subscription cannot post listings."""

    with app.app_context():
        user_id = _create_employer()

    response = client.post(
        "/listings",
        json=LISTING_PAYLOAD,
        headers=_auth_header(app, user_id),
    )
    assert response.status_code == 402
    assert "required" in response.get_json()["error"]


def test_listing_creation_consumes_credit(app, client):
    """Posting with listing credits decrements the available balance."""

    with app.app_context():
        user_id = _create_employer("credit2@example.com")
        subscription = EmployerSubscription(user_id=user_id, listing_credits=1)
        db.session.add(subscription)
        db.session.commit()

    response = client.post(
        "/listings",
        json=LISTING_PAYLOAD,
        headers=_auth_header(app, user_id),
    )
    assert response.status_code == 201

    with app.app_context():
        subscription = EmployerSubscription.query.filter_by(user_id=user_id).first()
        assert subscription.listing_credits == 0
        assert Listing.query.count() == 1


def test_listing_creation_allows_active_subscription(app, client):
    """Employers with an active subscription can post without consuming credits."""

    with app.app_context():
        user_id = _create_employer("subscribed@example.com")
        active_until = datetime.now(UTC) + timedelta(days=5)
        subscription = EmployerSubscription(
            user_id=user_id,
            listing_credits=0,
            active_until=active_until.replace(tzinfo=None),
        )
        db.session.add(subscription)
        db.session.commit()

    response = client.post(
        "/listings",
        json=LISTING_PAYLOAD,
        headers=_auth_header(app, user_id),
    )
    assert response.status_code == 201

    with app.app_context():
        subscription = EmployerSubscription.query.filter_by(user_id=user_id).first()
        assert subscription.listing_credits == 0
        assert Listing.query.count() == 1


def test_search_listings_supports_pagination_metadata(app, client):
    """Search listings returns paginated results with metadata."""

    with app.app_context():
        creator_id = _create_employer("paging@example.com")
        now = datetime.utcnow()
        listings = [
            Listing(
                category="job",
                title=f"Role {index}",
                description="desc",
                contact_method="email",
                contact_value="contact@example.com",
                is_public=True,
                is_active=True,
                created_by=creator_id,
                created_at=now + timedelta(seconds=index),
            )
            for index in range(5)
        ]
        db.session.add_all(listings)
        db.session.commit()

    response = client.get("/listings?page=2&per_page=2")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["count"] == 2
    assert [item["title"] for item in payload["results"]] == ["Role 2", "Role 1"]
    assert payload["pagination"] == {
        "page": 2,
        "per_page": 2,
        "total": 5,
        "total_pages": 3,
        "has_next": True,
        "has_prev": True,
    }


def test_search_listings_per_page_is_capped(app, client):
    """Search listings caps per_page at the route maximum."""

    with app.app_context():
        creator_id = _create_employer("paging-cap@example.com")
        now = datetime.utcnow()
        listings = [
            Listing(
                category="job",
                title=f"Cap Role {index}",
                description="desc",
                contact_method="email",
                contact_value="contact@example.com",
                is_public=True,
                is_active=True,
                created_by=creator_id,
                created_at=now + timedelta(seconds=index),
            )
            for index in range(101)
        ]
        db.session.add_all(listings)
        db.session.commit()

    response = client.get("/listings?page=1&per_page=1000")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["count"] == 100
    assert payload["pagination"]["per_page"] == 100
    assert payload["pagination"]["total"] == 101
    assert payload["pagination"]["total_pages"] == 2
