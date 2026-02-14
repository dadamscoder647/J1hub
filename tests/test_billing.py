"""Tests for billing webhook handling and account visibility endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flask_jwt_extended import create_access_token
import stripe

from models import db
from models.billing_event import BillingEvent
from models.employer_subscription import EmployerSubscription
from models.user import User


def _create_user(role: str = "employer", email: str = "employer@example.com") -> int:
    user = User(email=email, password_hash="hash", role=role)
    db.session.add(user)
    db.session.commit()
    return user.id


def _auth_header(app, user_id: int) -> dict[str, str]:
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def test_webhook_adds_listing_credits(app, client, monkeypatch):
    """Webhook should add listing credits for completed checkout sessions."""

    with app.app_context():
        user_id = _create_user()

    event = {
        "id": "evt_listing_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "user_id": str(user_id),
                    "billing_type": "listing",
                    "quantity": "3",
                }
            }
        },
    }

    def _mock_construct_event(payload, sig_header, secret):
        assert secret == app.config["STRIPE_WEBHOOK_SECRET"]
        return event

    monkeypatch.setattr(
        stripe.Webhook, "construct_event", staticmethod(_mock_construct_event)
    )

    response = client.post(
        "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "sig"}
    )
    assert response.status_code == 200

    with app.app_context():
        subscription = EmployerSubscription.query.filter_by(user_id=user_id).first()
        assert subscription is not None
        assert subscription.listing_credits == 3
        history = BillingEvent.query.filter_by(user_id=user_id).all()
        assert len(history) == 1
        assert history[0].event_type == "listing_credits_added"


def test_webhook_updates_subscription_period(app, client, monkeypatch):
    """Webhook should extend subscription active_until when invoices are paid."""

    with app.app_context():
        user_id = _create_user(email="sub@example.com")

    current_period_end = int((datetime.now(UTC) + timedelta(days=30)).timestamp())
    stripe_subscription = {
        "metadata": {"user_id": str(user_id), "billing_type": "subscription"},
        "current_period_end": current_period_end,
    }

    def _mock_construct_event(payload, sig_header, secret):
        return {
            "id": "evt_invoice_1",
            "type": "invoice.paid",
            "data": {"object": {"subscription": "sub_123"}},
        }

    def _mock_subscription_retrieve(subscription_id):
        assert subscription_id == "sub_123"
        return stripe_subscription

    monkeypatch.setattr(
        stripe.Webhook, "construct_event", staticmethod(_mock_construct_event)
    )
    monkeypatch.setattr(
        stripe.Subscription, "retrieve", staticmethod(_mock_subscription_retrieve)
    )

    response = client.post(
        "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "sig"}
    )
    assert response.status_code == 200

    with app.app_context():
        subscription = EmployerSubscription.query.filter_by(user_id=user_id).first()
        assert subscription is not None
        assert int(subscription.active_until.timestamp()) == current_period_end
        history = BillingEvent.query.filter_by(user_id=user_id).all()
        assert len(history) == 1
        assert history[0].event_type == "subscription_renewed"


def test_billing_status_requires_employer_or_admin(app, client):
    """Only employer/admin users should have visibility into billing status."""

    with app.app_context():
        worker_id = _create_user(role="worker", email="worker@example.com")

    response = client.get("/billing/status", headers=_auth_header(app, worker_id))
    assert response.status_code == 403


def test_billing_status_returns_account_snapshot(app, client):
    """Billing status should include credits and active subscription metadata."""

    with app.app_context():
        user_id = _create_user(email="credits@example.com")
        active_until = datetime.now(UTC) + timedelta(days=7)
        db.session.add(
            EmployerSubscription(
                user_id=user_id,
                listing_credits=4,
                active_until=active_until.replace(tzinfo=None),
            )
        )
        db.session.commit()

    response = client.get("/billing/status", headers=_auth_header(app, user_id))
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["listing_credits"] == 4
    assert payload["has_active_subscription"] is True
    assert payload["active_until"] is not None


def test_billing_history_returns_recent_events(app, client):
    """Billing history should return only the current user's events."""

    with app.app_context():
        user_id = _create_user(email="history@example.com")
        other_id = _create_user(email="other@example.com")
        db.session.add(
            BillingEvent(
                user_id=user_id,
                event_type="listing_credits_added",
                provider_event_id="evt_hist_1",
                details={"quantity": 2},
            )
        )
        db.session.add(
            BillingEvent(
                user_id=other_id,
                event_type="subscription_renewed",
                provider_event_id="evt_hist_2",
                details={"active_until": "2026-01-01T00:00:00"},
            )
        )
        db.session.commit()

    response = client.get(
        "/billing/history?limit=10",
        headers=_auth_header(app, user_id),
    )
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["events"][0]["provider_event_id"] == "evt_hist_1"


def test_billing_history_rejects_invalid_limit(app, client):
    """History endpoint should validate the limit query parameter."""

    with app.app_context():
        user_id = _create_user(email="limit@example.com")

    response = client.get(
        "/billing/history?limit=abc",
        headers=_auth_header(app, user_id),
    )
    assert response.status_code == 400
