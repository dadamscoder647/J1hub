"""Seed demo users, listings, and applications."""

from datetime import datetime, timedelta
from decimal import Decimal

from app import create_app
from models import db
from models.application import Application
from models.listing import Listing
from models.user import User
from scripts.seed_credentials import (
    DEFAULT_EMPLOYER_EMAIL,
    DEFAULT_EMPLOYER_PASSWORD,
    DEFAULT_WORKER_EMAIL,
    DEFAULT_WORKER_PASSWORD,
    get_seed_env_value,
)


def get_or_create_user(
    email: str,
    role: str,
    password: str,
    is_verified: bool = False,
) -> User:
    status = "approved" if is_verified else "unverified"
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(
            email=email,
            role=role,
            is_verified=is_verified,
            verification_status=status,
        )
        user.set_password(password)
        db.session.add(user)
    else:
        user.role = role
        if role != "admin":
            user.is_verified = is_verified
            user.verification_status = status
        user.set_password(password)
    return user


def main() -> None:
    employer_email = get_seed_env_value(
        "seed_demo_data", "SEED_EMPLOYER_EMAIL", DEFAULT_EMPLOYER_EMAIL
    )
    employer_password = get_seed_env_value(
        "seed_demo_data", "SEED_EMPLOYER_PASSWORD", DEFAULT_EMPLOYER_PASSWORD
    )
    worker_email = get_seed_env_value(
        "seed_demo_data", "SEED_WORKER_EMAIL", DEFAULT_WORKER_EMAIL
    )
    worker_password = get_seed_env_value(
        "seed_demo_data", "SEED_WORKER_PASSWORD", DEFAULT_WORKER_PASSWORD
    )

    app = create_app()
    with app.app_context():
        employer = get_or_create_user(
            employer_email, "employer", employer_password, is_verified=True
        )
        worker = get_or_create_user(
            worker_email, "worker", worker_password, is_verified=True
        )

        db.session.flush()

        listings_data = [
            {
                "category": "job",
                "title": "Resort Housekeeper",
                "description": "Seasonal housekeeping position at mountain resort.",
                "company_name": "Alpine Resort",
                "contact_method": "email",
                "contact_value": "hr@alpine.example",
                "location_city": "Aspen",
                "pay_rate": Decimal("17.50"),
                "currency": "USD",
                "shift": "Day",
                "is_public": True,
                "is_active": True,
                "expires_at": datetime.utcnow() + timedelta(days=60),
            },
            {
                "category": "housing",
                "title": "Shared Apartment Room",
                "description": "Furnished shared room close to public transit.",
                "company_name": "Sunset Rentals",
                "contact_method": "phone",
                "contact_value": "+1-555-0101",
                "location_city": "Chicago",
                "pay_rate": None,
                "currency": "USD",
                "shift": None,
                "is_public": True,
                "is_active": True,
                "expires_at": datetime.utcnow() + timedelta(days=45),
            },
            {
                "category": "ride",
                "title": "Airport Carpool",
                "description": "Ride from downtown to airport every Friday evening.",
                "company_name": "Community",
                "contact_method": "in_app",
                "contact_value": "message",
                "location_city": "Seattle",
                "pay_rate": Decimal("15.00"),
                "currency": "USD",
                "shift": "Evening",
                "is_public": False,
                "is_active": True,
                "expires_at": datetime.utcnow() + timedelta(days=14),
            },
        ]

        listings = []
        for data in listings_data:
            listing = Listing.query.filter_by(
                title=data["title"], created_by=employer.id
            ).first()
            if listing is None:
                listing = Listing(created_by=employer.id, **data)
                db.session.add(listing)
            else:
                for key, value in data.items():
                    setattr(listing, key, value)
            listings.append(listing)

        db.session.flush()

        first_listing = listings[0]
        existing_application = Application.query.filter_by(
            user_id=worker.id, listing_id=first_listing.id
        ).first()
        if existing_application is None:
            application = Application(
                user_id=worker.id,
                listing_id=first_listing.id,
                message="Excited to join the team!",
            )
            db.session.add(application)
        db.session.commit()

        print("Seed data inserted: employer, worker, listings, application.")


if __name__ == "__main__":
    main()
