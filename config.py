"""Application configuration module."""

import os
from pathlib import Path


class Config:
    """Base configuration for the Flask application."""

    # Core
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(Path("workspace") / "uploads"))

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
