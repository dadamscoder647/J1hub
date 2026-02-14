"""Add profile fields, saved listings, notifications, and application statuses."""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9f3d2b7c1a10"
down_revision = "1b5a52d73d61"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("skills", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("nationality", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("visa_type", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("visa_expiry", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("availability", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("company_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("company_website", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("company_size", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("company_industry", sa.String(length=120), nullable=True))

    op.add_column(
        "applications",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
    )

    op.create_table(
        "saved_listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "listing_id", name="uq_saved_listing"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("saved_listings")
    op.drop_column("applications", "status")

    op.drop_column("users", "company_industry")
    op.drop_column("users", "company_size")
    op.drop_column("users", "company_website")
    op.drop_column("users", "company_name")
    op.drop_column("users", "availability")
    op.drop_column("users", "visa_expiry")
    op.drop_column("users", "visa_type")
    op.drop_column("users", "nationality")
    op.drop_column("users", "skills")
