"""Shared pytest fixtures for the application tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.engine import make_url

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from config import Config
from models import db


def _test_database_uri() -> str:
    """Use only an explicitly approved local, disposable PostgreSQL test DB."""

    uri = os.environ.get("J1HUB_TEST_DATABASE_URL")
    if uri is None:
        return "sqlite:///:memory:"

    parsed = make_url(uri)
    if (
        parsed.drivername != "postgresql+psycopg"
        or parsed.host not in {"localhost", "127.0.0.1", "::1"}
        or not (parsed.database or "").endswith("_test")
        or parsed.query
        or os.environ.get("J1HUB_TEST_DATABASE_RESET") != "1"
    ):
        raise RuntimeError(
            "J1HUB_TEST_DATABASE_URL must target a loopback PostgreSQL *_test "
            "database, and J1HUB_TEST_DATABASE_RESET=1 must confirm it is disposable; "
            "the test fixture drops all ORM tables."
        )
    return uri


class _BaseTestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key-for-j1hub-tests-2026"
    JWT_SECRET_KEY = "test-jwt-secret-key-for-j1hub-tests-2026"
    SQLALCHEMY_DATABASE_URI = _test_database_uri()
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
