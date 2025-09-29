"""Tests for the Flask application factory."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from config import Config


class _BaseTestConfig(Config):
    """Base configuration for tests."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture()
def app(tmp_path) -> Flask:
    """Create a Flask application instance for tests."""

    upload_dir = tmp_path / "uploads"

    class TestConfig(_BaseTestConfig):
        UPLOAD_DIR = str(upload_dir)

    application = create_app(TestConfig)
    return application


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Return a test client for the Flask app."""

    return app.test_client()


def test_health_endpoint_returns_ok(client, tmp_path):
    """The health endpoint should respond with an OK payload."""

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert (tmp_path / "uploads").is_dir()


def test_blueprints_registered(app):
    """Application factory should register expected blueprints."""

    assert "verify" in app.blueprints
    assert "admin_verify" in app.blueprints
    assert "listings" in app.blueprints
