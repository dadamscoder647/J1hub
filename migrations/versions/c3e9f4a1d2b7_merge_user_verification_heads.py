"""Merge user verification migration branches.

Revision ID: c3e9f4a1d2b7
Revises: 1b5a52d73d61, b77b0a6c2c1a
Create Date: 2026-02-21
"""

# revision identifiers, used by Alembic.
revision = "c3e9f4a1d2b7"
down_revision = ("1b5a52d73d61", "b77b0a6c2c1a")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge branches without additional schema operations."""



def downgrade() -> None:
    """Split merged branches without additional schema operations."""
