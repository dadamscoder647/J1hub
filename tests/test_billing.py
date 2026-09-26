"""Tests for billing webhook handling and account visibility endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import stripe
from flask_jwt_extended import create_access_token

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


def _stub_stripe_client(
    monkeypatch, *, retrieve_subscription=None, create_checkout_session=None
):
    subscriptions = SimpleNamespace(
        retrieve=retrieve_subscription or (lambda *_args, **_kwargs: None)
    )
    checkout = SimpleNamespace(
        sessions=SimpleNamespace(
            create=create_checkout_session or (lambda *_args, **_kwargs: None)
        )
    )
    stripe_client = SimpleNamespace(
        v1=SimpleNamespace(subscriptions=subscriptions, checkout=checkout)
    )
    monkeypatch.setattr("routes.billing._get_stripe_client", lambda: stripe_client)
    return stripe_client


def test_webhook_requires_webhook_secret(app, client):
    """Webhook should return server configuration error when secret is missing."""

    app.config["STRIPE_WEBHOOK_SECRET"] = None

    response = client.post(
        "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "sig"}
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "Stripe webhook secret is not configured."}


def test_webhook_rejects_unsigned_payload(app, client):
    """Webhook should reject payloads that are not signed by Stripe."""

    response = client.post("/billing/webhook", data=b"{}")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid webhook signature."}


def test_webhook_adds_listing_credits(app, client, monkeypatch):
    """Webhook should add listing credits for completed checkout sessions."""

    with app.app_context():
        user_id = _create_user()

    event = {
        "id": "evt_listing_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "payment_status": "paid",
                "metadata": {
                    "user_id": str(user_id),
                    "billing_type": "listing",
                    "quantity": "3",
                },
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


def test_webhook_does_not_apply_a_duplicate_event_twice(app, client, monkeypatch):
    """Stripe retries with the same event id must not grant credits twice."""

    with app.app_context():
        user_id = _create_user(email="duplicate-event@example.com")

    event = {
        "id": "evt_listing_duplicate",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "payment_status": "paid",
                "metadata": {
                    "user_id": str(user_id),
                    "billing_type": "listing",
                    "quantity": "3",
                },
            }
        },
    }
    monkeypatch.setattr(
        stripe.Webhook, "construct_event", staticmethod(lambda *args: event)
    )
    headers = {"Stripe-Signature": "sig"}

    first = client.post("/billing/webhook", data=b"{}", headers=headers)
    second = client.post("/billing/webhook", data=b"{}", headers=headers)

    assert first.status_code == second.status_code == 200
    assert second.get_json() == {"status": "duplicate"}
    with app.app_context():
        subscription = EmployerSubscription.query.filter_by(user_id=user_id).first()
        history = BillingEvent.query.filter_by(
            provider_event_id="evt_listing_duplicate"
        ).all()
        assert subscription is not None
        assert subscription.listing_credits == 3
        assert len(history) == 1


def test_unpaid_checkout_does_not_activate_subscription(app, client, monkeypatch):
    """A completed but unpaid checkout must not start subscription access."""

    with app.app_context():
        user_id = _create_user(email="unpaid-subscription@example.com")

    event = {
        "id": "evt_subscription_unpaid",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_unpaid",
                "mode": "subscription",
                "payment_status": "unpaid",
                "subscription": "sub_unpaid",
                "metadata": {"user_id": str(user_id), "billing_type": "subscription"},
            }
        },
    }
    monkeypatch.setattr(
        stripe.Webhook, "construct_event", staticmethod(lambda *args: event)
    )
    _stub_stripe_client(
        monkeypatch,
        retrieve_subscription=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError(
                "unpaid checkout must not retrieve or activate a subscription"
            )
        ),
    )

    response = client.post(
        "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "sig"}
    )

    assert response.status_code == 200
    with app.app_context():
        assert EmployerSubscription.query.filter_by(user_id=user_id).first() is None


def test_async_checkout_success_grants_listing_credits(app, client, monkeypatch):
    """A delayed one-time payment grants credits only after async success."""

    with app.app_context():
        user_id = _create_user(email="async-payment@example.com")

    event = {
        "id": "evt_async_listing_paid",
        "type": "checkout.session.async_payment_succeeded",
        "data": {
            "object": {
                "id": "cs_async_paid",
                "payment_status": "paid",
                "metadata": {
                    "user_id": str(user_id),
                    "billing_type": "listing",
                    "quantity": "2",
                },
            }
        },
    }
    monkeypatch.setattr(
        stripe.Webhook, "construct_event", staticmethod(lambda *args: event)
    )
    _stub_stripe_client(monkeypatch)

    response = client.post(
        "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "sig"}
    )

    assert response.status_code == 200
    with app.app_context():
        subscription = EmployerSubscription.query.filter_by(user_id=user_id).first()
        assert subscription is not None
        assert subscription.listing_credits == 2


def test_async_checkout_failure_does_not_grant_listing_credits(
    app, client, monkeypatch
):
    """A delayed one-time payment failure is recorded without fulfillment."""

    with app.app_context():
        user_id = _create_user(email="async-payment-failed@example.com")

    event = {
        "id": "evt_async_listing_failed",
        "type": "checkout.session.async_payment_failed",
        "data": {
            "object": {
                "id": "cs_async_failed",
                "metadata": {
                    "user_id": str(user_id),
                    "billing_type": "listing",
                    "quantity": "2",
                },
            }
        },
    }
    monkeypatch.setattr(
        stripe.Webhook, "construct_event", staticmethod(lambda *args: event)
    )
    _stub_stripe_client(monkeypatch)

    response = client.post(
        "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "sig"}
    )

    assert response.status_code == 200
    with app.app_context():
        assert EmployerSubscription.query.filter_by(user_id=user_id).first() is None
        history = BillingEvent.query.filter_by(user_id=user_id).all()
        assert [item.event_type for item in history] == ["checkout_payment_failed"]


def test_subscription_checkout_uses_stripe_client(app, client, monkeypatch):
    """Subscription checkout uses StripeClient and returns the hosted session."""

    with app.app_context():
        user_id = _create_user(email="stripe-client@example.com")
    received = {}

    def _create_session(*, params):
        received.update(params)
        return SimpleNamespace(id="cs_test_123", url="https://checkout.example.test")

    _stub_stripe_client(monkeypatch, create_checkout_session=_create_session)

    response = client.post(
        "/billing/create-checkout-session",
        json={"purchase_type": "subscription"},
        headers=_auth_header(app, user_id),
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "sessionId": "cs_test_123",
        "url": "https://checkout.example.test",
    }
    assert received["mode"] == "subscription"
    assert received["line_items"] == [{"price": "price_monthly", "quantity": 1}]
    assert received["subscription_data"]["metadata"]["user_id"] == str(user_id)
    assert "payment_method_types" not in received


def test_webhook_updates_subscription_period(app, client, monkeypatch):
    """Webhook should extend subscription active_until when invoices are paid."""

    with app.app_context():
        user_id = _create_user(email="sub@example.com")

    current_period_end = int((datetime.now(UTC) + timedelta(days=30)).timestamp())
    stripe_subscription = SimpleNamespace(
        metadata={"user_id": str(user_id), "billing_type": "subscription"},
        items=SimpleNamespace(
            data=[SimpleNamespace(current_period_end=current_period_end)]
        ),
    )

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
    _stub_stripe_client(monkeypatch, retrieve_subscription=_mock_subscription_retrieve)

    response = client.post(
        "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "sig"}
    )
    assert response.status_code == 200

    with app.app_context():
        subscription = EmployerSubscription.query.filter_by(user_id=user_id).first()
        assert subscription is not None
        assert int(subscription.active_until.replace(tzinfo=UTC).timestamp()) == (
            current_period_end
        )
        history = BillingEvent.query.filter_by(user_id=user_id).all()
        assert len(history) == 1
        assert history[0].event_type == "subscription_renewed"


def test_cancellation_and_failed_payment_keep_access_through_paid_period(
    app, client, monkeypatch
):
    """Cancellation and failed payment preserve access until the paid-through date."""

    active_until = datetime.now(UTC) + timedelta(days=5)
    active_until_naive = active_until.replace(tzinfo=None)
    with app.app_context():
        user_id = _create_user(email="paid-through@example.com")
        db.session.add(
            EmployerSubscription(user_id=user_id, active_until=active_until_naive)
        )
        db.session.commit()

    cancellation_event = {
        "id": "evt_cancellation_scheduled",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_paid_through",
                "status": "canceled",
                "current_period_end": int(active_until.timestamp()),
                "metadata": {"user_id": str(user_id)},
            }
        },
    }
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        staticmethod(lambda *args: cancellation_event),
    )
    _stub_stripe_client(monkeypatch)

    cancellation_response = client.post(
        "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "sig"}
    )

    invoice_failure_event = {
        "id": "evt_renewal_failed",
        "type": "invoice.payment_failed",
        "data": {"object": {"id": "in_failed", "subscription": "sub_paid_through"}},
    }
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        staticmethod(lambda *args: invoice_failure_event),
    )
    _stub_stripe_client(
        monkeypatch,
        retrieve_subscription=lambda subscription_id: SimpleNamespace(
            id=subscription_id,
            metadata={"user_id": str(user_id)},
        ),
    )
    failure_response = client.post(
        "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "sig"}
    )

    assert cancellation_response.status_code == failure_response.status_code == 200
    with app.app_context():
        subscription = EmployerSubscription.query.filter_by(user_id=user_id).one()
        assert subscription.active_until == active_until_naive
        assert subscription.has_active_subscription(
            datetime.now(UTC).replace(tzinfo=None)
        )
        event_types = {
            event.event_type
            for event in BillingEvent.query.filter_by(user_id=user_id).all()
        }
        assert event_types == {"subscription_canceled", "subscription_payment_failed"}


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


def test_subscription_access_expires_at_paid_through_boundary():
    """Access expires at the paid-through timestamp."""

    paid_through = datetime(2030, 1, 1, tzinfo=UTC)
    subscription = EmployerSubscription(active_until=paid_through.replace(tzinfo=None))

    assert subscription.has_active_subscription(paid_through.replace(tzinfo=None)) is False
    assert (
        subscription.has_active_subscription(
            (paid_through - timedelta(microseconds=1)).replace(tzinfo=None)
        )
        is True
    )


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
