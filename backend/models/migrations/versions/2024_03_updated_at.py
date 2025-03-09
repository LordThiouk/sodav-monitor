"""Add updated_at column to users table

Revision ID: 2024_03_updated_at
Revises: 20250303_025425
Create Date: 2024-03-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '2024_03_updated_at'
down_revision = '20250303_025425'
branch_labels = None
depends_on = None


def upgrade():
    """Add updated_at column to users table."""
    # Add updated_at column to users table
    op.add_column('users', sa.Column('updated_at', sa.TIMESTAMP(), nullable=True))
    
    # Set default value for existing rows
    op.execute("UPDATE users SET updated_at = created_at WHERE updated_at IS NULL")
    
    # Make the column not nullable
    op.alter_column('users', 'updated_at', nullable=False)


def downgrade():
    """Remove updated_at column from users table."""
    op.drop_column('users', 'updated_at') 