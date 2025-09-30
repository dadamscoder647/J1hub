"""Tests for the Flask application factory."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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
    assert "billing" in app.blueprints
