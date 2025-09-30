"""Billing and Stripe integration endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
import stripe

from models import db
from models.employer_subscription import EmployerSubscription
from models.user import User

billing_bp = Blueprint("billing", __name__)


def _get_employer(user_id: int | str | None) -> User | None:
    """Return the employer user for the given identifier."""

    if user_id is None:
        return None
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None
    return User.query.get(user_id)


def _get_or_create_subscription(user_id: int) -> EmployerSubscription:
    subscription = EmployerSubscription.query.filter_by(user_id=user_id).first()
    if subscription is None:
        subscription = EmployerSubscription(user_id=user_id, listing_credits=0)
        db.session.add(subscription)
    return subscription


def _init_stripe() -> str | None:
    """Configure Stripe with the API key from configuration."""

    api_key = current_app.config.get("STRIPE_SECRET_KEY")
    if not api_key:
        return None
    stripe.api_key = api_key
    return api_key


@billing_bp.route("/create-checkout-session", methods=["POST"])
@jwt_required()
def create_checkout_session():
    """Create a Stripe Checkout session for credits or subscription."""

    api_key = _init_stripe()
    if not api_key:
        return (
            jsonify({"error": "Stripe secret key is not configured."}),
            500,
        )

    user_id = get_jwt_identity()
    user = _get_employer(user_id)
    if user is None or user.role not in {"employer", "admin"}:
        return (
            jsonify({"error": "Only employers or admins can start billing sessions."}),
            403,
        )

    data = request.get_json() or {}
    purchase_type = data.get("purchase_type", "listing")

    success_url = data.get("success_url") or current_app.config.get("BILLING_SUCCESS_URL")
    cancel_url = data.get("cancel_url") or current_app.config.get("BILLING_CANCEL_URL")
    if not success_url or not cancel_url:
        return (
            jsonify({"error": "Billing success and cancel URLs must be configured."}),
            400,
        )

    try:
        if purchase_type == "listing":
            price_id = current_app.config.get("PRICE_LISTING")
            if not price_id:
                return jsonify({"error": "Listing price is not configured."}), 500
            quantity = data.get("quantity", 1)
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                return jsonify({"error": "quantity must be an integer"}), 400
            if quantity <= 0:
                return jsonify({"error": "quantity must be greater than zero"}), 400
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{"price": price_id, "quantity": quantity}],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": str(user.id),
                    "billing_type": "listing",
                    "quantity": str(quantity),
                },
            )
        elif purchase_type == "subscription":
            price_id = current_app.config.get("PRICE_MONTHLY")
            if not price_id:
                return jsonify({"error": "Subscription price is not configured."}), 500
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": str(user.id),
                    "billing_type": "subscription",
                },
                subscription_data={
                    "metadata": {
                        "user_id": str(user.id),
                        "billing_type": "subscription",
                    }
                },
            )
        else:
            return jsonify({"error": "purchase_type must be listing or subscription."}), 400
    except stripe.error.StripeError as exc:  # pragma: no cover - network error
        return jsonify({"error": str(exc)}), 502

    return jsonify({"sessionId": session.id, "url": session.url})


def _handle_listing_purchase(metadata: dict) -> None:
    user_id = metadata.get("user_id")
    if not user_id:
        return
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return
    quantity_raw = metadata.get("quantity")
    try:
        quantity = int(quantity_raw) if quantity_raw is not None else 1
    except (TypeError, ValueError):
        quantity = 1
    quantity = max(quantity, 1)

    subscription = _get_or_create_subscription(user_id_int)
    subscription.listing_credits = (subscription.listing_credits or 0) + quantity


def _set_subscription_active(user_id: int, current_period_end: int | None) -> None:
    if current_period_end is None:
        return
    subscription = _get_or_create_subscription(user_id)
    new_expiration = datetime.fromtimestamp(current_period_end, UTC).replace(tzinfo=None)
    if not subscription.active_until or subscription.active_until < new_expiration:
        subscription.active_until = new_expiration


def _handle_subscription_event(subscription_id: str | None) -> None:
    if not subscription_id:
        return
    try:
        subscription_obj = stripe.Subscription.retrieve(subscription_id)
    except stripe.error.StripeError:  # pragma: no cover - network error
        return
    metadata = subscription_obj.get("metadata", {})
    user_id = metadata.get("user_id")
    if not user_id:
        return
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return
    current_period_end = subscription_obj.get("current_period_end")
    _set_subscription_active(user_id_int, current_period_end)


@billing_bp.route("/webhook", methods=["POST"])
def billing_webhook():
    """Handle Stripe webhook events for billing updates."""

    api_key = _init_stripe()
    if not api_key:
        return jsonify({"error": "Stripe secret key is not configured."}), 500

    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:  # pragma: no cover - fallback path
            event = stripe.Event.construct_from(request.get_json(force=True), stripe.api_key)
    except (ValueError, stripe.error.SignatureVerificationError):
        return jsonify({"error": "Invalid webhook signature."}), 400

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})
    metadata = data_object.get("metadata", {})

    if event_type == "checkout.session.completed":
        billing_type = metadata.get("billing_type")
        if billing_type == "listing":
            _handle_listing_purchase(metadata)
        elif billing_type == "subscription":
            subscription_id = data_object.get("subscription")
            _handle_subscription_event(subscription_id)
    elif event_type == "invoice.paid":
        subscription_id = data_object.get("subscription")
        _handle_subscription_event(subscription_id)

    db.session.commit()
    return jsonify({"status": "success"})
