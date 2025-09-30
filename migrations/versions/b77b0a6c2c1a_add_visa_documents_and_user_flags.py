"""Create visa_documents table and add user verification fields."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "b77b0a6c2c1a"
down_revision = "8a2f5e85a0e4"
branch_labels = None
depends_on = None


VISA_DOCUMENT_STATUS_ENUM = "visa_document_status"
USER_VERIFICATION_STATUS_ENUM = "verification_status"


def upgrade() -> None:
    """Apply the visa document and user column changes."""

    bind = op.get_bind()
    inspector = inspect(bind)

    if "visa_documents" in inspector.get_table_names():
        existing_indexes = {index["name"] for index in inspector.get_indexes("visa_documents")}
        index_name = op.f("ix_visa_documents_user_id")
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="visa_documents")
        op.drop_table("visa_documents")
        op.execute(f"DROP TYPE IF EXISTS {VISA_DOCUMENT_STATUS_ENUM}")

    visa_document_status = sa.Enum(
        "pending",
        "approved",
        "rejected",
        name=VISA_DOCUMENT_STATUS_ENUM,
    )
    visa_document_status.create(bind, checkfirst=True)

    op.create_table(
        "visa_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            visa_document_status,
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "waiver_acknowledged",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_visa_documents_user_id"),
        "visa_documents",
        ["user_id"],
        unique=False,
    )

    user_columns = {column["name"] for column in inspector.get_columns("users")}

    verification_status_enum = sa.Enum(
        "unverified",
        "pending",
        "approved",
        "rejected",
        name=USER_VERIFICATION_STATUS_ENUM,
    )

    if "verification_status" in user_columns:
        op.alter_column(
            "users",
            "verification_status",
            existing_type=verification_status_enum,
            type_=sa.String(length=32),
            existing_nullable=False,
            postgresql_using="verification_status::text",
        )
        op.execute(f"DROP TYPE IF EXISTS {USER_VERIFICATION_STATUS_ENUM}")
    else:
        op.add_column(
            "users",
            sa.Column(
                "verification_status",
                sa.String(length=32),
                nullable=False,
                server_default=sa.text("'unverified'"),
            ),
        )
        op.alter_column("users", "verification_status", server_default=None)

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
        op.alter_column("users", "is_active", server_default=None)


def downgrade() -> None:
    """Revert the visa document and user column changes."""

    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if "users" in table_names:
        user_columns = {column["name"] for column in inspector.get_columns("users")}

        if "is_active" in user_columns:
            op.drop_column("users", "is_active")

        if "verification_status" in user_columns:
            verification_status_enum = sa.Enum(
                "unverified",
                "pending",
                "approved",
                "rejected",
                name=USER_VERIFICATION_STATUS_ENUM,
            )
            verification_status_enum.create(bind, checkfirst=True)
            op.alter_column(
                "users",
                "verification_status",
                existing_type=sa.String(length=32),
                type_=verification_status_enum,
                existing_nullable=False,
                postgresql_using="verification_status::verification_status",
            )

    if "visa_documents" in table_names:
        existing_indexes = {index["name"] for index in inspector.get_indexes("visa_documents")}
        index_name = op.f("ix_visa_documents_user_id")
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="visa_documents")
        op.drop_table("visa_documents")
    op.execute(f"DROP TYPE IF EXISTS {VISA_DOCUMENT_STATUS_ENUM}")
