"""Shared input validation for credentials used by seed scripts."""

from __future__ import annotations

import os


def get_seed_env_value(script_name: str, env_var: str) -> str:
    """Return a required seed value without falling back to predictable credentials."""
    value = os.getenv(env_var)
    if not value or not value.strip():
        raise RuntimeError(
            f"{env_var} must be set to a non-empty value before running {script_name}."
        )
    return value.strip()
