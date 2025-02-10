"""merge heads fingerprint

Revision ID: merge_heads_fingerprint
Revises: add_fingerprint_columns, merge_heads_reports
Create Date: 2025-02-10 02:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads_fingerprint'
down_revision = ('add_fingerprint_columns', 'merge_heads_reports')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass 