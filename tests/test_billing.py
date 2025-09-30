"""Tests for billing webhook handling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import stripe

from models import db
from models.employer_subscription import EmployerSubscription
from models.user import User


def _create_employer(email: str = "employer@example.com") -> int:
    user = User(email=email, password_hash="hash", role="employer")
    db.session.add(user)
    db.session.commit()
    return user.id


def test_webhook_adds_listing_credits(app, client, monkeypatch):
    """Webhook should add listing credits for completed checkout sessions."""

    with app.app_context():
        user_id = _create_employer()

    event = {
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


def test_webhook_updates_subscription_period(app, client, monkeypatch):
    """Webhook should extend subscription active_until when invoices are paid."""

    with app.app_context():
        user_id = _create_employer("sub@example.com")

    current_period_end = int((datetime.now(UTC) + timedelta(days=30)).timestamp())
    stripe_subscription = {
        "metadata": {"user_id": str(user_id), "billing_type": "subscription"},
        "current_period_end": current_period_end,
    }

    def _mock_construct_event(payload, sig_header, secret):
        return {
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
