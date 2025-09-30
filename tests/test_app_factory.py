"""Tests for the Flask application factory."""

from __future__ import annotations

import pytest



def test_health_endpoint_returns_ok(client, tmp_path):
    """The health endpoint should respond with an OK payload."""

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert (tmp_path / "uploads").is_dir()


def test_blueprints_registered(app):
    """Application factory should register expected blueprints."""

    assert "auth" in app.blueprints
    assert "verify" in app.blueprints
    assert "admin_verify" in app.blueprints
    assert "listings" in app.blueprints
