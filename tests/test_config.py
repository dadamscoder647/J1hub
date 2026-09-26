"""Tests for environment-derived frontend configuration."""

from sqlalchemy import create_engine

from config import _frontend_settings, _normalize_database_url


def test_render_postgres_url_schemes_select_psycopg():
    for scheme in ("postgres://", "postgresql://"):
        value = f"{scheme}user:pass@db.example:5432/j1hub"

        assert _normalize_database_url(value) == (
            "postgresql+psycopg://user:pass@db.example:5432/j1hub"
        )
        engine = create_engine(_normalize_database_url(value))
        try:
            assert engine.dialect.name == "postgresql"
            assert engine.dialect.driver == "psycopg"
        finally:
            engine.dispose()


def test_explicit_driver_and_non_postgres_database_urls_are_preserved():
    psycopg_url = "postgresql+psycopg://user:pass@db.example:5432/j1hub"
    sqlite_url = "sqlite:///app.db"

    assert _normalize_database_url(psycopg_url) == psycopg_url
    assert _normalize_database_url(sqlite_url) == sqlite_url


def test_frontend_url_supplies_cors_and_billing_return_defaults():
    origins, success_url, cancel_url = _frontend_settings(
        "https://j1hub.example/", None, None, None
    )

    assert origins == ["https://j1hub.example"]
    assert success_url == (
        "https://j1hub.example/billing/success?session_id={CHECKOUT_SESSION_ID}"
    )
    assert cancel_url == "https://j1hub.example/billing/cancel"


def test_explicit_frontend_settings_override_generated_defaults():
    origins, success_url, cancel_url = _frontend_settings(
        "https://j1hub.example",
        "https://app.example, https://admin.example",
        "https://checkout.example/success",
        "https://checkout.example/cancel",
    )

    assert origins == ["https://app.example", "https://admin.example"]
    assert success_url == "https://checkout.example/success"
    assert cancel_url == "https://checkout.example/cancel"


def test_missing_frontend_url_preserves_wildcard_and_missing_billing_urls():
    origins, success_url, cancel_url = _frontend_settings(None, None, None, None)

    assert origins == "*"
    assert success_url is None
    assert cancel_url is None
