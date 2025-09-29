"""add listings and applications tables"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "listings_20240609"
down_revision = "visa_doc_20230929"
branch_labels = None
depends_on = None


LISTING_CATEGORIES = ("jobs", "housing", "rides", "gigs")


def upgrade():
    listing_category_enum = sa.Enum(*LISTING_CATEGORIES, name="listing_category_enum")
    listing_category_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", listing_category_enum, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("company_name", sa.String(length=120), nullable=True),
        sa.Column("contact_method", sa.String(length=50), nullable=False),
        sa.Column("contact_value", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("pay_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("shift", sa.String(length=120), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_listings_category", "listings", ["category"])
    op.create_index("ix_listings_city", "listings", ["city"])
    op.create_index("ix_listings_is_active", "listings", ["is_active"])

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("listing_id", sa.Integer(), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_applications_listing_id", "applications", ["listing_id"])
    op.create_index("ix_applications_user_id", "applications", ["user_id"])


def downgrade():
    op.drop_index("ix_applications_user_id", table_name="applications")
    op.drop_index("ix_applications_listing_id", table_name="applications")
    op.drop_table("applications")

    op.drop_index("ix_listings_is_active", table_name="listings")
    op.drop_index("ix_listings_city", table_name="listings")
    op.drop_index("ix_listings_category", table_name="listings")
    op.drop_table("listings")

    listing_category_enum = sa.Enum(*LISTING_CATEGORIES, name="listing_category_enum")
    listing_category_enum.drop(op.get_bind(), checkfirst=True)
