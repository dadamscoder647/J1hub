"""Switch user verification status to string and add active flag."""

import sqlalchemy as sa
from alembic import op
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

    if verification_status_column and (
        verification_status_is_enum
        or getattr(verification_status_type, "length", None) != 32
    ):
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
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "verification_status_tmp",
                existing_type=sa.String(length=32),
                existing_nullable=False,
                server_default=None,
            )
            batch_op.drop_column("verification_status")
            batch_op.alter_column(
                "verification_status_tmp",
                new_column_name="verification_status",
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

        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "is_active",
                existing_type=sa.Boolean(),
                existing_nullable=False,
                server_default=None,
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

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "verification_status_old",
            existing_type=verification_status_enum,
            existing_nullable=False,
            server_default=None,
        )
        batch_op.drop_column("verification_status")
        batch_op.alter_column(
            "verification_status_old",
            new_column_name="verification_status",
            existing_type=verification_status_enum,
        )
