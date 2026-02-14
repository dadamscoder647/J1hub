"""Tests for domain flows: profiles, favorites, applications, and notifications."""

from __future__ import annotations

from flask_jwt_extended import create_access_token

from models import db
from models.application import Application
from models.listing import Listing
from models.notification import Notification
from models.saved_listing import SavedListing
from models.user import User
from models.visa_document import VisaDocument
from routes.billing import _handle_listing_purchase


LISTING_PAYLOAD = {
    "category": "job",
    "title": "Seasonal worker",
    "description": "Help needed",
    "contact_method": "email",
    "contact_value": "boss@example.com",
}


def _create_user(email: str, role: str = "worker", verified: bool = True) -> User:
    user = User(email=email, password_hash="hash", role=role, is_verified=verified)
    db.session.add(user)
    db.session.commit()
    return user


def _auth_header(app, user_id: int) -> dict[str, str]:
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def _create_listing(owner_id: int) -> Listing:
    listing = Listing(created_by=owner_id, **LISTING_PAYLOAD)
    db.session.add(listing)
    db.session.commit()
    return listing


def test_profile_fields_update_by_role(app, client):
    with app.app_context():
        worker = _create_user("worker-profile@example.com", "worker")
        employer = _create_user("employer-profile@example.com", "employer")
        worker_id = worker.id
        employer_id = employer.id

    response = client.patch(
        "/auth/me",
        json={"skills": "python,flask", "nationality": "JP", "availability": "full-time"},
        headers=_auth_header(app, worker_id),
    )
    assert response.status_code == 200
    assert response.get_json()["user"]["skills"] == "python,flask"

    response = client.patch(
        "/auth/me",
        json={"company_name": "Acme Co", "company_industry": "Hospitality"},
        headers=_auth_header(app, employer_id),
    )
    assert response.status_code == 200
    assert response.get_json()["user"]["company_name"] == "Acme Co"


def test_saved_listing_lifecycle_and_authorization(app, client):
    with app.app_context():
        employer = _create_user("employer-fav@example.com", "employer")
        worker = _create_user("worker-fav@example.com", "worker")
        listing = _create_listing(employer.id)
        employer_id = employer.id
        worker_id = worker.id
        listing_id = listing.id

    create_resp = client.post(
        f"/listings/{listing_id}/favorite",
        headers=_auth_header(app, worker_id),
    )
    assert create_resp.status_code == 201

    list_resp = client.get("/listings/favorites", headers=_auth_header(app, worker_id))
    assert list_resp.status_code == 200
    assert list_resp.get_json()["count"] == 1

    forbidden_resp = client.get("/listings/favorites", headers=_auth_header(app, employer_id))
    assert forbidden_resp.status_code == 403

    delete_resp = client.delete(
        f"/listings/{listing_id}/favorite",
        headers=_auth_header(app, worker_id),
    )
    assert delete_resp.status_code == 200

    with app.app_context():
        assert SavedListing.query.count() == 0


def test_application_status_lifecycle_and_authorization(app, client):
    with app.app_context():
        employer = _create_user("employer-app@example.com", "employer")
        other_employer = _create_user("other-employer@app.com", "employer")
        worker = _create_user("worker-app@example.com", "worker")
        listing = _create_listing(employer.id)
        employer_id = employer.id
        other_employer_id = other_employer.id
        worker_id = worker.id
        listing_id = listing.id

    submit_resp = client.post(
        f"/listings/{listing_id}/apply",
        json={"message": "Interested"},
        headers=_auth_header(app, worker_id),
    )
    assert submit_resp.status_code == 201
    application_id = submit_resp.get_json()["id"]
    assert submit_resp.get_json()["status"] == "new"

    list_for_employer = client.get(
        f"/listings/{listing_id}/applications",
        headers=_auth_header(app, employer_id),
    )
    assert list_for_employer.status_code == 200
    assert list_for_employer.get_json()["count"] == 1

    forbidden_update = client.patch(
        f"/listings/{listing_id}/applications/{application_id}",
        json={"status": "reviewing"},
        headers=_auth_header(app, other_employer_id),
    )
    assert forbidden_update.status_code == 403

    for status in ["reviewing", "accepted", "rejected"]:
        update_resp = client.patch(
            f"/listings/{listing_id}/applications/{application_id}",
            json={"status": status},
            headers=_auth_header(app, employer_id),
        )
        assert update_resp.status_code == 200
        assert update_resp.get_json()["status"] == status

    mine_resp = client.get("/listings/applications/mine", headers=_auth_header(app, worker_id))
    assert mine_resp.status_code == 200
    assert mine_resp.get_json()["results"][0]["status"] == "rejected"

    with app.app_context():
        assert Application.query.get(application_id).status == "rejected"
        assert Notification.query.filter_by(user_id=worker_id, event_type="application_update").count() == 3


def test_verification_and_billing_notifications(app, client):
    with app.app_context():
        admin = _create_user("admin-verify@example.com", "admin")
        worker = _create_user("worker-verify@example.com", "worker")
        admin_id = admin.id
        worker_id = worker.id
        worker.verification_status = "pending"
        doc = VisaDocument(
            user_id=worker_id,
            filename="visa.pdf",
            file_path="visa.pdf",
            file_type="application/pdf",
            waiver_acknowledged=True,
            status="pending",
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    verify_resp = client.post(
        f"/verify/{doc_id}/approve",
        headers=_auth_header(app, admin_id),
    )
    assert verify_resp.status_code == 200

    with app.app_context():
        _handle_listing_purchase({"user_id": str(worker_id), "quantity": "2"})
        db.session.commit()
        assert Notification.query.filter_by(user_id=worker_id, event_type="verification_result").count() == 1
        assert Notification.query.filter_by(user_id=worker_id, event_type="billing_credit_change").count() == 1
