"""Application configuration module."""

import os
from pathlib import Path


class Config:
    """Base configuration for the Flask application.

    Environment variables:
        MAX_UPLOAD_SIZE: Maximum upload size in bytes (default 10 MB).
        ALLOWED_UPLOAD_TYPES: Comma-separated list of allowed MIME types for uploads.
    """

    # Core
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    TESTING = os.getenv("TESTING", "false").lower() == "true"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    ENV = os.getenv("FLASK_ENV") or os.getenv("ENV") or "production"
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(Path("workspace") / "uploads"))
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))
    ALLOWED_UPLOAD_TYPES = os.getenv(
        "ALLOWED_UPLOAD_TYPES", "image/jpeg,image/png,application/pdf"
    ).split(",")

    # CORS
    _raw_origins = os.getenv("ORIGINS", "*")
    if _raw_origins.strip() == "*":
        CORS_ORIGINS = "*"
    else:
        CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

    # Rate limiting
    RATE_LIMIT = os.getenv("RATE_LIMIT", "60 per minute")
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_KEY_PREFIX = os.getenv("RATELIMIT_KEY_PREFIX", "")

    # Stripe / billing (optional)
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    PRICE_LISTING = os.getenv("PRICE_LISTING")
    PRICE_MONTHLY = os.getenv("PRICE_MONTHLY")
    BILLING_SUCCESS_URL = os.getenv("BILLING_SUCCESS_URL")
    BILLING_CANCEL_URL = os.getenv("BILLING_CANCEL_URL")

    _INSECURE_SECRET_VALUES = {"", "change-me", "changeme", "default", "placeholder"}

    @classmethod
    def should_enforce_secret_validation(cls) -> bool:
        """Return whether strict secret validation should be enforced."""
        return not bool(getattr(cls, "TESTING", False)) and not (
            bool(getattr(cls, "DEBUG", False))
            or str(getattr(cls, "ENV", "")).lower() == "development"
        )

    @classmethod
    def validate_security_settings(cls) -> None:
        """Validate runtime security settings for non-safe environments."""
        if not cls.should_enforce_secret_validation():
            return

        secret_key = str(getattr(cls, "SECRET_KEY", "") or "").strip()
        jwt_secret_key = str(getattr(cls, "JWT_SECRET_KEY", "") or "").strip()

        missing_or_insecure = []
        if secret_key.lower() in cls._INSECURE_SECRET_VALUES:
            missing_or_insecure.append("SECRET_KEY")
        if jwt_secret_key.lower() in cls._INSECURE_SECRET_VALUES:
            missing_or_insecure.append("JWT_SECRET_KEY")

        if missing_or_insecure:
            keys = ", ".join(missing_or_insecure)
            raise RuntimeError(
                f"Refusing to start with insecure default secrets ({keys}). "
                "Set strong SECRET_KEY and JWT_SECRET_KEY values in the environment."
            )
