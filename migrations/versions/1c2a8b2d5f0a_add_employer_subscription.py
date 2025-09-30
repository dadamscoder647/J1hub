"""Add employer subscription table.

Revision ID: 1c2a8b2d5f0a
Revises: 6d6be07685c8
Create Date: 2025-10-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1c2a8b2d5f0a"
down_revision = "6d6be07685c8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "employer_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("active_until", sa.DateTime(), nullable=True),
        sa.Column(
            "listing_credits",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_employer_subscriptions_user_id"),
    )


def downgrade():
    op.drop_table("employer_subscriptions")
