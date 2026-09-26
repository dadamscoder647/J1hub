"""Tests for explicit, non-default seed credentials."""

import pytest

from scripts.seed_credentials import get_seed_env_value


@pytest.mark.parametrize("environment_variable", ["APP_ENV", "FLASK_ENV", "ENV"])
def test_seed_values_are_required_even_with_local_environment_labels(
    monkeypatch, environment_variable
):
    for variable in ("APP_ENV", "FLASK_ENV", "ENV"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv(environment_variable, "development")
    monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="SEED_ADMIN_PASSWORD must be set"):
        get_seed_env_value("seed_admin", "SEED_ADMIN_PASSWORD")


def test_seed_value_rejects_whitespace_only_values(monkeypatch):
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "   ")

    with pytest.raises(RuntimeError, match="SEED_ADMIN_PASSWORD must be set"):
        get_seed_env_value("seed_admin", "SEED_ADMIN_PASSWORD")


def test_seed_value_strips_explicit_value(monkeypatch):
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "  admin@example.test  ")

    assert get_seed_env_value("seed_admin", "SEED_ADMIN_EMAIL") == "admin@example.test"
