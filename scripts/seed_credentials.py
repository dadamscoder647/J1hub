"""Shared seed credential helpers for local scripts."""

from __future__ import annotations

import os
import sys

DEFAULT_ADMIN_EMAIL = "admin@example.com"  # Local-development default
DEFAULT_ADMIN_PASSWORD = "AdminPass123"  # Local-development default
DEFAULT_EMPLOYER_EMAIL = "employer@example.com"  # Local-development default
DEFAULT_EMPLOYER_PASSWORD = "EmployerPass123"  # Local-development default
DEFAULT_WORKER_EMAIL = "worker@example.com"  # Local-development default
DEFAULT_WORKER_PASSWORD = "WorkerPass123"  # Local-development default


def get_seed_env_value(script_name: str, env_var: str, default: str) -> str:
    """Return an env value or fallback to local-development defaults with warning."""

    value = os.getenv(env_var)
    if value:
        return value

    default_preview = "[redacted]" if "PASSWORD" in env_var else repr(default)
    print(
        (
            f"[{script_name}] WARNING: {env_var} is not set. "
            f"Using local-development default value: {default_preview}."
        ),
        file=sys.stderr,
    )
    return default
