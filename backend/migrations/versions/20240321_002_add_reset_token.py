"""add reset token columns

Revision ID: 20240321_002_add_reset_token
Revises: 20240321_001_merge_heads
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20240321_002_add_reset_token'
down_revision = '20240321_001_merge_heads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add reset_token and reset_token_expires columns
    op.add_column('users', sa.Column('reset_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_token_expires', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'reset_token_expires')
    op.drop_column('users', 'reset_token') 