"""Update visa document model.

Revision ID: d4d19a25492d
Revises: 1c2a8b2d5f0a
Create Date: 2025-09-30 04:08:13.758484
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d4d19a25492d"
down_revision = "1c2a8b2d5f0a"
branch_labels = None
depends_on = None


VISA_DOCUMENT_STATUS_NAME = "visa_document_status"


def upgrade():
    """Apply the visa document schema changes."""

    op.drop_table("visa_documents")
    op.execute(f"DROP TYPE IF EXISTS {VISA_DOCUMENT_STATUS_NAME}")
    op.execute("DROP TYPE IF EXISTS visa_document_type")

    op.create_table(
        "visa_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                name=VISA_DOCUMENT_STATUS_NAME,
            ),
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
    op.create_index(
        op.f("ix_visa_documents_user_id"),
        "visa_documents",
        ["user_id"],
        unique=False,
    )


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
            sa.Enum("passport", "j1_visa", name="visa_document_type"),
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
