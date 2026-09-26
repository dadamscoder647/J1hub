"""Merge the integrated product feature migration heads.

Revision ID: f0e1d2c3b4a5
Revises: c3e9f4a1d2b7, 9f3d2b7c1a10, 9f6f4a1d2a7b, 2f4c6b8a9d10
Create Date: 2026-09-25
"""

# revision identifiers, used by Alembic.
revision = "f0e1d2c3b4a5"
down_revision = (
    "c3e9f4a1d2b7",
    "9f3d2b7c1a10",
    "9f6f4a1d2a7b",
    "2f4c6b8a9d10",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Join feature migrations without changing the schema."""


def downgrade() -> None:
    """Split feature migration branches without changing the schema."""
