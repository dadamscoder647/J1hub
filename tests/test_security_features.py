"""Tests covering security and hardening features."""

from __future__ import annotations

import secrets
import sys
from pathlib import Path

import pytest
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


def _valid_production_signing_keys() -> dict[str, str]:
    return {
        "SECRET_KEY": secrets.token_urlsafe(32),
        "JWT_SECRET_KEY": secrets.token_urlsafe(32),
    }


def test_cors_allows_configured_origin(tmp_path):
    app = _build_app(tmp_path, CORS_ORIGINS=["https://client.example"])
    client = app.test_client()

    response = client.get("/health", headers={"Origin": "https://client.example"})

    assert response.status_code == 200
    assert (
        response.headers.get("Access-Control-Allow-Origin") == "https://client.example"
    )
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


def test_rate_limit_prefix_is_stable_outside_tests(tmp_path):
    strong_keys = {
        "APP_ENV": "production",
        "TESTING": False,
        **_valid_production_signing_keys(),
    }
    first_app = _build_app(tmp_path, **strong_keys)
    second_app = _build_app(tmp_path, **strong_keys)

    assert first_app.config["RATELIMIT_KEY_PREFIX"] == "j1hub:"
    assert second_app.config["RATELIMIT_KEY_PREFIX"] == "j1hub:"


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


def test_legacy_aliases_can_be_disabled(tmp_path):
    app = _build_app(tmp_path, API_ENABLE_LEGACY_ROUTES=False)
    client = app.test_client()

    legacy = client.get("/verify/status")
    canonical = client.get("/api/v1/verify/status")

    assert legacy.status_code == 404
    assert canonical.status_code == 401
    assert client.get("/health").status_code == 404
    assert client.get("/api/v1/health").status_code == 200


def test_production_requires_secret_keys(tmp_path):
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _build_app(
            tmp_path,
            APP_ENV="production",
            TESTING=False,
            SECRET_KEY="change-me",
            JWT_SECRET_KEY="change-me",
        )


def test_development_environment_label_does_not_allow_example_secrets(tmp_path):
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        _build_app(
            tmp_path,
            APP_ENV="development",
            TESTING=False,
            DEBUG=False,
            SECRET_KEY="replace-with-long-random-secret",
            JWT_SECRET_KEY="replace-with-long-random-jwt-secret",
        )


def test_production_rejects_identical_signing_keys(tmp_path):
    shared_key = "shared-signing-key-with-more-than-32-characters"
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        _build_app(
            tmp_path,
            APP_ENV="production",
            TESTING=False,
            SECRET_KEY=shared_key,
            JWT_SECRET_KEY=shared_key,
        )


@pytest.mark.parametrize(
    "checked_in_key",
    [
        "ci-secret-only-test-key-for-j1hub-unit-workflows",
        "ci-jwt-secret-only-test-key-for-j1hub-workflows",
        "ci-secret-only-test-key-for-j1hub-migration-workflows",
        "ci-jwt-secret-only-test-key-for-j1hub-migrations",
        "test-secret-key-for-j1hub-tests-2026",
        "test-jwt-secret-key-for-j1hub-tests-2026",
    ],
)
@pytest.mark.parametrize("key_name", ["SECRET_KEY", "JWT_SECRET_KEY"])
def test_production_rejects_checked_in_test_and_ci_signing_keys(
    tmp_path, checked_in_key, key_name
):
    settings = {
        "APP_ENV": "production",
        "TESTING": False,
        **_valid_production_signing_keys(),
    }
    settings[key_name] = checked_in_key

    with pytest.raises(RuntimeError, match=key_name):
        _build_app(tmp_path, **settings)


def test_production_rejects_case_and_whitespace_variants_of_checked_in_keys(tmp_path):
    settings = {
        "APP_ENV": "production",
        "TESTING": False,
        **_valid_production_signing_keys(),
    }
    settings["SECRET_KEY"] = "  TEST-SECRET-KEY-FOR-J1HUB-TESTS-2026  "

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _build_app(tmp_path, **settings)


def test_debug_flag_is_rejected_outside_explicit_development_config(tmp_path):
    with pytest.raises(RuntimeError, match="DEBUG must be false"):
        _build_app(
            tmp_path,
            APP_ENV="production",
            TESTING=False,
            DEBUG=True,
            **_valid_production_signing_keys(),
        )


def test_production_requires_stripe_webhook_when_stripe_enabled(tmp_path):
    with pytest.raises(RuntimeError, match="STRIPE_WEBHOOK_SECRET"):
        _build_app(
            tmp_path,
            APP_ENV="production",
            TESTING=False,
            **_valid_production_signing_keys(),
            STRIPE_SECRET_KEY="sk_live_value",
            STRIPE_WEBHOOK_SECRET=None,
        )
