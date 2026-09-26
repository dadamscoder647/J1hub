"""Application configuration module."""

import os
from pathlib import Path
from typing import ClassVar


class Config:
    """Base configuration for the Flask application.

    Environment variables:
        MAX_UPLOAD_SIZE: Maximum upload size in bytes (default 10 MB).
        ALLOWED_UPLOAD_RULES: Mapping of extension -> allowed MIME type(s) for uploads.
    """

    # Core
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    ENV = os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or os.getenv("ENV") or "production"
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(Path("workspace") / "uploads"))
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))
    ALLOWED_UPLOAD_RULES: ClassVar[dict[str, list[str]]] = {
        "pdf": ["application/pdf"],
        "png": ["image/png"],
        "jpg": ["image/jpeg"],
        "jpeg": ["image/jpeg"],
    }
    # Backwards-compatible flattened MIME list consumed by older checks.
    ALLOWED_UPLOAD_TYPES: ClassVar[list[str]] = [
        mime.strip().lower()
        for mime in os.getenv(
            "ALLOWED_UPLOAD_TYPES", "image/jpeg,image/png,application/pdf"
        ).split(",")
        if mime.strip()
    ]

    # CORS
    _raw_origins = os.getenv("ORIGINS", "*")
    CORS_ORIGINS: str | list[str]
    if _raw_origins.strip() == "*":
        CORS_ORIGINS = "*"
    else:
        CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

    # Rate limiting
    RATE_LIMIT = os.getenv("RATE_LIMIT", "60 per minute")
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_KEY_PREFIX = os.getenv("RATELIMIT_KEY_PREFIX", "")

    # API versioning
    API_ENABLE_LEGACY_ROUTES = os.getenv("API_ENABLE_LEGACY_ROUTES", "true").lower() == "true"

    # Stripe / billing (optional)
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    PRICE_LISTING = os.getenv("PRICE_LISTING")
    PRICE_MONTHLY = os.getenv("PRICE_MONTHLY")
    BILLING_SUCCESS_URL = os.getenv("BILLING_SUCCESS_URL")
    BILLING_CANCEL_URL = os.getenv("BILLING_CANCEL_URL")


class DevelopmentConfig(Config):
    """Local developer configuration with temporary keys for convenience."""

    DEBUG = True
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key")


class TestingConfig(Config):
    """Testing configuration with lightweight temporary keys."""

    TESTING = True
    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-jwt-secret-key"
