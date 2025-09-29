"""create visa_documents table and user.is_verified

Revision ID: visa_doc_20230929
Revises: 
Create Date: 2024-03-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "visa_doc_20230929"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        "visa_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column(
            "doc_type",
            sa.Enum("passport", "j1_visa", name="doc_type_enum"),
            nullable=False,
        ),
        sa.Column("file_url", sa.String(length=256), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "denied", name="status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_visa_documents_user_id", "visa_documents", ["user_id"])
    op.create_index("ix_visa_documents_status", "visa_documents", ["status"])


def downgrade() -> None:
    op.drop_index("ix_visa_documents_status", table_name="visa_documents")
    op.drop_index("ix_visa_documents_user_id", table_name="visa_documents")
    op.drop_table("visa_documents")
    op.drop_column("user", "is_verified")
    op.execute("DROP TYPE IF EXISTS doc_type_enum")
    op.execute("DROP TYPE IF EXISTS status_enum")
