"""Update visa document model.

Revision ID: d4d19a25492d
Revises: 1c2a8b2d5f0a
Create Date: 2025-09-30 04:08:13.758484
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "d4d19a25492d"
down_revision = "1c2a8b2d5f0a"
branch_labels = None
depends_on = None


VISA_DOCUMENT_STATUS_NAME = "visa_document_status"
OLD_VISA_DOCUMENT_TYPE_NAME = "visa_document_type"


NEW_STATUS_ENUM = sa.Enum(
    "pending",
    "approved",
    "rejected",
    name=VISA_DOCUMENT_STATUS_NAME,
)


def _backfill_filename(bind) -> None:
    """Backfill filename values from file_path/file_url using SQL."""

    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            """
            UPDATE visa_documents
            SET filename = COALESCE(
                NULLIF(regexp_replace(file_path, '^.*/', ''), ''),
                file_path,
                'migrated_document'
            )
            WHERE filename IS NULL OR filename = ''
            """
        )
        return

    # SQLite fallback: preserve full path value when basename helpers are unavailable.
    op.execute(
        """
        UPDATE visa_documents
        SET filename = COALESCE(NULLIF(file_path, ''), 'migrated_document')
        WHERE filename IS NULL OR filename = ''
        """
    )


def _migrate_old_to_new_columns(bind) -> None:
    """Transform legacy visa_documents columns into the new schema."""

    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("visa_documents")}

    # Rename columns first to preserve legacy data.
    with op.batch_alter_table("visa_documents") as batch_op:
        if "file_url" in columns and "file_path" not in columns:
            batch_op.alter_column("file_url", new_column_name="file_path")
        if "notes" in columns and "review_note" not in columns:
            batch_op.alter_column("notes", new_column_name="review_note")

    # Add new columns that did not exist in the legacy schema.
    refreshed_columns = {
        column["name"] for column in inspect(bind).get_columns("visa_documents")
    }

    with op.batch_alter_table("visa_documents") as batch_op:
        if "filename" not in refreshed_columns:
            batch_op.add_column(sa.Column("filename", sa.String(length=255), nullable=True))
        if "file_type" not in refreshed_columns:
            batch_op.add_column(sa.Column("file_type", sa.String(length=128), nullable=True))
        if "reviewer_id" not in refreshed_columns:
            batch_op.add_column(sa.Column("reviewer_id", sa.Integer(), nullable=True))

    # Backfill values from old fields with explicit SQL updates.
    refreshed_columns = {
        column["name"] for column in inspect(bind).get_columns("visa_documents")
    }

    if "doc_type" in refreshed_columns:
        op.execute(
            """
            UPDATE visa_documents
            SET file_type = CASE
                WHEN doc_type = 'passport' THEN 'passport'
                WHEN doc_type = 'j1_visa' THEN 'j1_visa'
                ELSE 'other'
            END
            WHERE file_type IS NULL
            """
        )

    if "file_path" in refreshed_columns and "filename" in refreshed_columns:
        _backfill_filename(bind)


def _migrate_status_enum() -> None:
    """Map legacy status values and migrate status enum definition."""

    op.execute("UPDATE visa_documents SET status='rejected' WHERE status='denied'")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE visa_documents ALTER COLUMN status TYPE VARCHAR(32) USING status::text"
        )
        op.execute(f"DROP TYPE IF EXISTS {VISA_DOCUMENT_STATUS_NAME}")
        NEW_STATUS_ENUM.create(bind, checkfirst=True)
        op.execute(
            f"ALTER TABLE visa_documents ALTER COLUMN status TYPE {VISA_DOCUMENT_STATUS_NAME} USING status::{VISA_DOCUMENT_STATUS_NAME}"
        )


def upgrade():
    """Apply the visa document schema changes without dropping existing data."""

    bind = op.get_bind()
    inspector = inspect(bind)

    if "visa_documents" not in inspector.get_table_names():
        op.create_table(
            "visa_documents",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=False),
            sa.Column("file_path", sa.String(length=512), nullable=False),
            sa.Column("file_type", sa.String(length=128), nullable=False),
            sa.Column(
                "status",
                NEW_STATUS_ENUM,
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column("reviewer_id", sa.Integer(), nullable=True),
            sa.Column("review_note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        _migrate_old_to_new_columns(bind)
        _migrate_status_enum()

        # Remove legacy doc_type after its values are copied to file_type.
        columns = {column["name"] for column in inspect(bind).get_columns("visa_documents")}
        if "doc_type" in columns:
            with op.batch_alter_table("visa_documents") as batch_op:
                batch_op.drop_column("doc_type")

        with op.batch_alter_table("visa_documents") as batch_op:
            batch_op.alter_column("filename", existing_type=sa.String(length=255), nullable=False)
            batch_op.alter_column("file_path", existing_type=sa.String(length=512), nullable=False)
            batch_op.alter_column("file_type", existing_type=sa.String(length=128), nullable=False)
            batch_op.alter_column("status", nullable=False, server_default=sa.text("'pending'"))

    index_name = op.f("ix_visa_documents_user_id")
    existing_indexes = {index["name"] for index in inspect(bind).get_indexes("visa_documents")}
    if index_name not in existing_indexes:
        op.create_index(index_name, "visa_documents", ["user_id"], unique=False)

    # best-effort cleanup for legacy enum not used anymore.
    op.execute(f"DROP TYPE IF EXISTS {OLD_VISA_DOCUMENT_TYPE_NAME}")


def downgrade():
    """Revert the visa document schema changes."""

    op.drop_index(op.f("ix_visa_documents_user_id"), table_name="visa_documents")
    op.drop_table("visa_documents")
    op.execute(f"DROP TYPE IF EXISTS {VISA_DOCUMENT_STATUS_NAME}")

    op.create_table(
        "visa_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "doc_type",
            sa.Enum("passport", "j1_visa", name=OLD_VISA_DOCUMENT_TYPE_NAME),
            nullable=False,
        ),
        sa.Column("file_url", sa.String(length=512), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "denied", name=VISA_DOCUMENT_STATUS_NAME),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
