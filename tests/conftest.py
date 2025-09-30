"""Shared pytest fixtures for the application tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app  # noqa: E402
from config import Config  # noqa: E402
from models import db  # noqa: E402


class _BaseTestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STRIPE_SECRET_KEY = "sk_test"
    STRIPE_WEBHOOK_SECRET = "whsec_test"
    PRICE_LISTING = "price_listing"
    PRICE_MONTHLY = "price_monthly"
    BILLING_SUCCESS_URL = "https://example.com/success"
    BILLING_CANCEL_URL = "https://example.com/cancel"


@pytest.fixture()
def app(tmp_path) -> Flask:
    """Create a Flask application instance for tests."""

    upload_dir = tmp_path / "uploads"

    class TestConfig(_BaseTestConfig):
        UPLOAD_DIR = str(upload_dir)

    application = create_app(TestConfig)

    with application.app_context():
        db.create_all()

    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Return a test client for the Flask app."""

    return app.test_client()
