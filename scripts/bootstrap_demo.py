"""Bootstrap demo data for local development."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from models import db
from models.listing import Listing
from models.user import User
from scripts.seed_credentials import (
    DEFAULT_ADMIN_EMAIL,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_EMPLOYER_EMAIL,
    DEFAULT_EMPLOYER_PASSWORD,
    DEFAULT_WORKER_EMAIL,
    DEFAULT_WORKER_PASSWORD,
    get_seed_env_value,
)


@dataclass
class CreatedRecords:
    """Container for created or updated record identifiers."""

    admin_id: int
    employer_id: int
    worker_id: int
    listing_id: int


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

    listing = Listing.query.filter_by(title=LISTING_TITLE, created_by=owner_id).first()
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

    admin_email = get_seed_env_value(
        "bootstrap_demo", "SEED_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL
    )
    admin_password = get_seed_env_value(
        "bootstrap_demo", "SEED_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD
    )
    employer_email = get_seed_env_value(
        "bootstrap_demo", "SEED_EMPLOYER_EMAIL", DEFAULT_EMPLOYER_EMAIL
    )
    employer_password = get_seed_env_value(
        "bootstrap_demo", "SEED_EMPLOYER_PASSWORD", DEFAULT_EMPLOYER_PASSWORD
    )
    worker_email = get_seed_env_value(
        "bootstrap_demo", "SEED_WORKER_EMAIL", DEFAULT_WORKER_EMAIL
    )
    worker_password = get_seed_env_value(
        "bootstrap_demo", "SEED_WORKER_PASSWORD", DEFAULT_WORKER_PASSWORD
    )

    app = create_app()
    with app.app_context():
        db.create_all()

        admin = get_or_create_user(admin_email, admin_password, "admin")
        employer = get_or_create_user(employer_email, employer_password, "employer")
        worker = get_or_create_user(worker_email, worker_password, "worker")

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
