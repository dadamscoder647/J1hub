"""Create visa_documents table and add user verification fields."""

import sqlalchemy as sa
from alembic import op
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

    if "visa_documents" not in inspector.get_table_names():
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

    current_document_columns = {
        column["name"] for column in inspect(bind).get_columns("visa_documents")
    }
    required_document_columns = {
        "id",
        "user_id",
        "filename",
        "file_path",
        "file_type",
        "status",
        "reviewer_id",
        "review_note",
        "waiver_acknowledged",
        "created_at",
    }
    missing_document_columns = required_document_columns - current_document_columns
    if missing_document_columns:
        missing = ", ".join(sorted(missing_document_columns))
        raise RuntimeError(
            "Refusing to replace visa_documents because its existing schema is "
            f"incomplete (missing: {missing}). Resolve it with a data-preserving "
            "migration before retrying."
        )

    existing_indexes = {
        index["name"] for index in inspect(bind).get_indexes("visa_documents")
    }
    index_name = op.f("ix_visa_documents_user_id")
    if index_name not in existing_indexes:
        op.create_index(index_name, "visa_documents", ["user_id"], unique=False)

    user_columns = {column["name"]: column for column in inspector.get_columns("users")}

    if "verification_status" in user_columns:
        verification_status_type = user_columns["verification_status"]["type"]
        if hasattr(verification_status_type, "enums"):
            op.alter_column(
                "users",
                "verification_status",
                existing_type=verification_status_type,
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
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "verification_status",
                existing_type=sa.String(length=32),
                existing_nullable=False,
                server_default=None,
            )

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
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "is_active",
                existing_type=sa.Boolean(),
                existing_nullable=False,
                server_default=None,
            )


def downgrade() -> None:
    """Keep shared tables and columns required by the sibling migration branch.

    Revision 1b5a52d73d61 already owns the overlapping user fields, and its
    parent chain already owns visa_documents. Dropping them here would erase
    data when Alembic splits the merged heads.
    """
