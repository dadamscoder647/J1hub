"""Tests for the Flask application factory."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def test_health_endpoint_returns_ok(client, tmp_path):
    """The health endpoint should respond with an OK payload and create uploads dir."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    # uploads dir is configured via TestConfig in conftest and created on app init
    assert (tmp_path / "uploads").is_dir()


def test_blueprints_registered(app):
    """Application factory should register expected blueprints."""
    bps = set(app.blueprints.keys())
    required = {"auth", "verify", "listings"}
    assert required.issubset(bps)
    # billing is optional; do not require it for tests


def test_startup_validation_raises_when_keys_missing(tmp_path):
    """Non-testing app startup should fail when required secure keys are absent."""

    from app import create_app
    from config import Config

    class MissingKeyConfig(Config):
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        UPLOAD_DIR = str(tmp_path / "uploads")
        SECRET_KEY = None
        JWT_SECRET_KEY = None

    with pytest.raises(RuntimeError, match="Missing required security configuration"):
        create_app(MissingKeyConfig)


def test_dev_config_allows_local_temp_keys(tmp_path):
    """Development config should allow temporary fallback keys for local dev ergonomics."""

    from app import create_app
    from config import DevelopmentConfig

    class LocalDevConfig(DevelopmentConfig):
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        UPLOAD_DIR = str(tmp_path / "uploads")

    app = create_app(LocalDevConfig)

    assert app.config["SECRET_KEY"]
    assert app.config["JWT_SECRET_KEY"]
