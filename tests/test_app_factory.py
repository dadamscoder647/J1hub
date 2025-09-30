"""Tests for the Flask application factory."""
from __future__ import annotations

import sys
from pathlib import Path

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
    required = {"auth", "verify", "admin_verify", "listings"}
    assert required.issubset(bps)
    # billing is optional; do not require it for tests
