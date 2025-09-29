"""Pytest fixtures for the application."""

from collections.abc import Generator
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app, db
from models import User


@pytest.fixture
def app_instance(tmp_path: Path) -> Generator:
    app = create_app(
        SQLALCHEMY_DATABASE_URI="sqlite://",
        TESTING=True,
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
        UPLOAD_URL_PREFIX="/uploads",
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


@pytest.fixture
def user_id(app_instance):
    with app_instance.app_context():
        user = User(email="user@example.com", password_hash="hashed", role="user")
        db.session.add(user)
        db.session.commit()
        return user.id
