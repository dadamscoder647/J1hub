"""Application configuration module."""

import os
from pathlib import Path


class Config:
    """Base configuration for the Flask application."""

    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_DIR = os.getenv(
        "UPLOAD_DIR", str(Path("workspace") / "uploads")
    )
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    PRICE_LISTING = os.getenv("PRICE_LISTING")
    PRICE_MONTHLY = os.getenv("PRICE_MONTHLY")
    BILLING_SUCCESS_URL = os.getenv("BILLING_SUCCESS_URL")
    BILLING_CANCEL_URL = os.getenv("BILLING_CANCEL_URL")
