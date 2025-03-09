"""merge heads

Revision ID: 20240321_004_merge_heads
Revises: 20240321_002_add_reset_token, 20240321_003_add_track_metadata
Create Date: 2024-03-02 22:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240321_004_merge_heads'
down_revision = ('20240321_002_add_reset_token', '20240321_003_add_track_metadata')
branch_labels = None
depends_on = None

def upgrade() -> None:
    # This is a merge migration, no upgrade needed
    pass

def downgrade() -> None:
    # This is a merge migration, no downgrade needed
    pass 