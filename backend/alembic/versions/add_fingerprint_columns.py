"""add fingerprint columns

Revision ID: add_fingerprint_columns
Revises: merge_heads_reports
Create Date: 2025-02-10 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_fingerprint_columns'
down_revision = 'merge_heads_reports'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add fingerprint columns to tracks table
    with op.batch_alter_table('tracks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fingerprint', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('fingerprint_raw', sa.ARRAY(sa.Integer()), nullable=True))
        
        # Create index on fingerprint for faster lookups
        batch_op.create_index('ix_tracks_fingerprint', ['fingerprint'], unique=False)

def downgrade() -> None:
    # Remove fingerprint columns from tracks table
    with op.batch_alter_table('tracks', schema=None) as batch_op:
        batch_op.drop_index('ix_tracks_fingerprint')
        batch_op.drop_column('fingerprint_raw')
        batch_op.drop_column('fingerprint') 