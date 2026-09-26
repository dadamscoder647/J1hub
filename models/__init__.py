"""Database initialization and model exports."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models to register them with SQLAlchemy metadata.
from .application import Application
from .billing_event import BillingEvent
from .employer_subscription import EmployerSubscription
from .listing import Listing
from .notification import Notification
from .saved_listing import SavedListing
from .user import User
from .visa_document import VisaDocument

__all__ = [
    "Application",
    "BillingEvent",
    "EmployerSubscription",
    "Listing",
    "Notification",
    "SavedListing",
    "User",
    "VisaDocument",
    "db",
]
