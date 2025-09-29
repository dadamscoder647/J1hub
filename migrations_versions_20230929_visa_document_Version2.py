"""add VisaDocument and is_verified to User

Revision ID: visa_doc_20230929
Revises: 
Create Date: 2025-09-29 02:59:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'visa_doc_20230929'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('user', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        'visa_documents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('doc_type', sa.Enum('passport', 'j1_visa', name='doc_type_enum'), nullable=False),
        sa.Column('file_url', sa.String(256), nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'denied', name='status_enum'), nullable=False, server_default='pending'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('visa_documents')
    op.drop_column('user', 'is_verified')
    op.execute("DROP TYPE IF EXISTS doc_type_enum")
    op.execute("DROP TYPE IF EXISTS status_enum")