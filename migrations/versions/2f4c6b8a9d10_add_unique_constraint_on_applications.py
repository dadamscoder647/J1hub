"""Add unique constraint for one application per user/listing pair."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "2f4c6b8a9d10"
down_revision = ("1b5a52d73d61", "b77b0a6c2c1a")
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "uq_applications_user_id_listing_id"


def upgrade() -> None:
    """Apply the applications uniqueness guarantee safely."""

    bind = op.get_bind()
    inspector = inspect(bind)

    duplicate = bind.execute(
        sa.text(
        """
        SELECT user_id, listing_id, COUNT(*) AS duplicate_count
        FROM applications
        GROUP BY user_id, listing_id
        HAVING COUNT(*) > 1
        LIMIT 1
        """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot enforce one application per worker/listing while duplicate "
            f"rows remain for user_id={duplicate.user_id}, listing_id={duplicate.listing_id}. "
            "Review and resolve those rows before retrying this migration."
    )

    existing_unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("applications")
        if constraint.get("name")
    }

    if CONSTRAINT_NAME not in existing_unique_constraints:
        with op.batch_alter_table("applications") as batch_op:
            batch_op.create_unique_constraint(
                CONSTRAINT_NAME,
                ["user_id", "listing_id"],
            )


def downgrade() -> None:
    """Remove the applications unique constraint."""

    bind = op.get_bind()
    inspector = inspect(bind)
    existing_unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("applications")
        if constraint.get("name")
    }

    if CONSTRAINT_NAME in existing_unique_constraints:
        with op.batch_alter_table("applications") as batch_op:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="unique")
