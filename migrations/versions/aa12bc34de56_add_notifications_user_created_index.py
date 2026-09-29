"""Add an index for user-scoped notification pagination."""

from alembic import op

# revision identifiers, used by Alembic.
revision = "aa12bc34de56"
down_revision = "f0e1d2c3b4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_notifications_user_created_id",
        "notifications",
        ["user_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_created_id", table_name="notifications")
