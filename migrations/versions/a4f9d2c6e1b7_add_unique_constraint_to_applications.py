"""Add unique constraint for applications by user and listing.

Revision ID: a4f9d2c6e1b7
Revises: 1b5a52d73d61
Create Date: 2026-02-14 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a4f9d2c6e1b7"
down_revision = "1b5a52d73d61"
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "uq_applications_user_listing"


def upgrade() -> None:
    """Apply schema changes."""

    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "applications",
        ["user_id", "listing_id"],
    )


def downgrade() -> None:
    """Revert schema changes."""

    op.drop_constraint(CONSTRAINT_NAME, "applications", type_="unique")
