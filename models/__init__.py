"""Database initialization and model exports."""

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()

# Import models to register them with SQLAlchemy metadata.
from .user import User  # noqa: E402,F401
from .visa_document import VisaDocument  # noqa: E402,F401
from .listing import Listing  # noqa: E402,F401
from .application import Application  # noqa: E402,F401
from .employer_subscription import EmployerSubscription  # noqa: E402,F401

__all__ = [
    "db",
    "User",
    "VisaDocument",
    "Listing",
    "Application",
    "EmployerSubscription",
]
