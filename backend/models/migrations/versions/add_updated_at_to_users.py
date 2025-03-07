"""Add updated_at to users table

Revision ID: 2024_03_updated_at
Create Date: 2024-03-03 17:48:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic
revision = '2024_03_updated_at'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add updated_at column with default value
    op.add_column('users',
        sa.Column('updated_at', sa.DateTime(), 
                  nullable=False, 
                  server_default=sa.text('now()'))
    )

def downgrade() -> None:
    # Remove the column in downgrade
    op.drop_column('users', 'updated_at')