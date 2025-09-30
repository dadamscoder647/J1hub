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
    _raw_origins = os.getenv("ORIGINS", "*")
    if _raw_origins == "*":
        CORS_ORIGINS = "*"
    else:
        CORS_ORIGINS = [
            origin.strip()
            for origin in _raw_origins.split(",")
            if origin.strip()
        ]
    RATE_LIMIT = os.getenv("RATE_LIMIT", "60 per minute")
