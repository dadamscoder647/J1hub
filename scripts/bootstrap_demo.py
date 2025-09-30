"""Bootstrap demo data for local development."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from models import db
from models.listing import Listing
from models.user import User


@dataclass
class CreatedRecords:
    """Container for created or updated record identifiers."""

    admin_id: int
    employer_id: int
    worker_id: int
    listing_id: int


ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "AdminPass123"
EMPLOYER_EMAIL = "boss@example.com"
EMPLOYER_PASSWORD = "BossPass123"
WORKER_EMAIL = "j1@example.com"
WORKER_PASSWORD = "J1Pass123"
LISTING_TITLE = "Seasonal Hospitality Associate"


def get_or_create_user(email: str, password: str, role: str) -> User:
    """Create or update a user with the provided credentials."""

    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(
            email=email,
            role=role,
            is_verified=True,
            verification_status="approved",
        )
        user.set_password(password)
        db.session.add(user)
    else:
        user.role = role
        user.is_verified = True
        user.verification_status = "approved"
        user.set_password(password)
    return user


def create_listing(owner_id: int) -> Listing:
    """Ensure a public job listing exists for the employer."""

    listing = Listing.query.filter_by(
        title=LISTING_TITLE, created_by=owner_id
    ).first()
    if listing is None:
        listing = Listing(
            category="job",
            title=LISTING_TITLE,
            description=(
                "Join our hospitality team for the upcoming season. "
                "Provide excellent guest experiences and support daily operations."
            ),
            company_name="J1 Hospitality Group",
            contact_method="email",
            contact_value="recruiting@j1hospitality.example",
            location_city="Denver",
            pay_rate=Decimal("18.00"),
            currency="USD",
            shift="Full-time",
            is_public=True,
            is_active=True,
            created_by=owner_id,
        )
        db.session.add(listing)
    else:
        listing.category = "job"
        listing.description = (
            "Join our hospitality team for the upcoming season. "
            "Provide excellent guest experiences and support daily operations."
        )
        listing.company_name = "J1 Hospitality Group"
        listing.contact_method = "email"
        listing.contact_value = "recruiting@j1hospitality.example"
        listing.location_city = "Denver"
        listing.pay_rate = Decimal("18.00")
        listing.currency = "USD"
        listing.shift = "Full-time"
        listing.is_public = True
        listing.is_active = True
    return listing


def bootstrap() -> CreatedRecords:
    """Bootstrap the demo records and return their identifiers."""

    app = create_app()
    with app.app_context():
        db.create_all()

        admin = get_or_create_user(ADMIN_EMAIL, ADMIN_PASSWORD, "admin")
        employer = get_or_create_user(EMPLOYER_EMAIL, EMPLOYER_PASSWORD, "employer")
        worker = get_or_create_user(WORKER_EMAIL, WORKER_PASSWORD, "worker")

        db.session.flush()

        listing = create_listing(owner_id=employer.id)

        db.session.commit()

        return CreatedRecords(
            admin_id=admin.id,
            employer_id=employer.id,
            worker_id=worker.id,
            listing_id=listing.id,
        )


if __name__ == "__main__":
    records = bootstrap()
    print(json.dumps(asdict(records)))
