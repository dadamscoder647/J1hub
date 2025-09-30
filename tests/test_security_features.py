"""Tests covering security and hardening features."""

from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from config import Config


class _SecurityBaseConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def _build_app(tmp_path: Path, **overrides) -> Flask:
    upload_dir = tmp_path / "uploads"

    class TestConfig(_SecurityBaseConfig):
        UPLOAD_DIR = str(upload_dir)

    for key, value in overrides.items():
        setattr(TestConfig, key, value)

    return create_app(TestConfig)


def test_cors_allows_configured_origin(tmp_path):
    app = _build_app(tmp_path, CORS_ORIGINS=["https://client.example"])
    client = app.test_client()

    response = client.get(
        "/health", headers={"Origin": "https://client.example"}
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "https://client.example"
    assert response.headers.get("X-Request-ID")


def test_rate_limit_exceeded_returns_json(tmp_path):
    app = _build_app(tmp_path, RATE_LIMIT="2 per minute")
    client = app.test_client()

    client.get("/health")
    client.get("/health")
    response = client.get("/health")

    assert response.status_code == 429
    payload = response.get_json()
    assert payload["error"] == "Too Many Requests"
    assert "request_id" in payload


def test_json_error_shape_for_invalid_request(tmp_path):
    app = _build_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/auth/register",
        data="not-json",
        content_type="text/plain",
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "Bad Request"
    assert "Request content type" in payload["detail"]
    assert payload["request_id"]
