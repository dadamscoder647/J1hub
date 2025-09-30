"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from config import Config
from models import db


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
def client(app: Flask):
    """Return a test client for the Flask app."""

    return app.test_client()


@pytest.fixture()
def db_session(app: Flask):
    """Provide a database session with tables created for each test."""

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()
