"""Switch user verification status to string and add active flag."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "1b5a52d73d61"
down_revision = "8a2f5e85a0e4"
branch_labels = None
depends_on = None


VERIFICATION_STATUS_ENUM = "verification_status"
VERIFICATION_STATUS_VALUES = (
    "unverified",
    "pending",
    "approved",
    "rejected",
)


def upgrade() -> None:
    """Apply the verification status and activation updates."""

    bind = op.get_bind()
    inspector = inspect(bind)
    user_columns = {column["name"]: column for column in inspector.get_columns("users")}

    verification_status_column = user_columns.get("verification_status")
    verification_status_type = verification_status_column["type"] if verification_status_column else None
    verification_status_is_enum = hasattr(verification_status_type, "enums")

    if verification_status_column and verification_status_is_enum:
        op.add_column(
            "users",
            sa.Column(
                "verification_status_tmp",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'unverified'"),
            ),
        )
        op.execute("UPDATE users SET verification_status_tmp = verification_status")
        op.alter_column(
            "users",
            "verification_status_tmp",
            server_default=None,
            existing_type=sa.String(length=32),
        )

        op.drop_column("users", "verification_status")
        op.alter_column(
            "users",
            "verification_status_tmp",
            new_column_name="verification_status",
            existing_type=sa.String(length=32),
        )
        op.alter_column(
            "users",
            "verification_status",
            server_default=None,
            existing_type=sa.String(length=32),
        )

    verification_status_enum = sa.Enum(name=VERIFICATION_STATUS_ENUM)
    verification_status_enum.drop(bind, checkfirst=True)

    if "is_active" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )

        users = sa.table("users", sa.column("is_active", sa.Boolean()))
        op.execute(users.update().where(users.c.is_active.is_(None)).values(is_active=True))

        op.alter_column(
            "users",
            "is_active",
            server_default=None,
            existing_type=sa.Boolean(),
        )


def downgrade() -> None:
    """Revert the verification status and activation updates."""

    op.drop_column("users", "is_active")

    verification_status_enum = sa.Enum(
        *VERIFICATION_STATUS_VALUES, name=VERIFICATION_STATUS_ENUM
    )
    verification_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "verification_status_old",
            verification_status_enum,
            nullable=False,
            server_default=sa.text("'unverified'"),
        ),
    )

    op.execute(
        """
        UPDATE users
        SET verification_status_old = CASE
            WHEN verification_status IN ('unverified', 'pending', 'approved', 'rejected')
                THEN verification_status
            ELSE 'unverified'
        END
        """
    )

    op.alter_column(
        "users",
        "verification_status_old",
        server_default=None,
        existing_type=verification_status_enum,
    )

    op.drop_column("users", "verification_status")
    op.alter_column(
        "users",
        "verification_status_old",
        new_column_name="verification_status",
        existing_type=verification_status_enum,
    )
