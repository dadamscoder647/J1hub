"""Add verification status tracking to users and visa documents."""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8a2f5e85a0e4"
down_revision = "d4d19a25492d"
branch_labels = None
depends_on = None


VERIFICATION_STATUS_ENUM = "verification_status"


def upgrade() -> None:
    """Apply the verification status schema changes."""

    verification_status = sa.Enum(
        "unverified",
        "pending",
        "approved",
        "rejected",
        name=VERIFICATION_STATUS_ENUM,
    )
    verification_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "verification_status",
            verification_status,
            nullable=False,
            server_default=sa.text("'unverified'"),
        ),
    )
    op.execute(
        "UPDATE users SET verification_status='approved' WHERE is_verified = 1"
    )
    op.alter_column("users", "verification_status", server_default=None)

    op.add_column(
        "visa_documents",
        sa.Column(
            "waiver_acknowledged",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        "UPDATE visa_documents SET waiver_acknowledged=0 WHERE waiver_acknowledged IS NULL"
    )
    op.alter_column(
        "visa_documents",
        "waiver_acknowledged",
        server_default=None,
    )


def downgrade() -> None:
    """Revert the verification status schema changes."""

    op.drop_column("visa_documents", "waiver_acknowledged")

    op.drop_column("users", "verification_status")
    verification_status = sa.Enum(name=VERIFICATION_STATUS_ENUM)
    verification_status.drop(op.get_bind(), checkfirst=True)
