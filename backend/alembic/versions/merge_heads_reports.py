"""merge heads reports

Revision ID: merge_heads_reports
Revises: add_user_id_to_reports, fix_report_status
Create Date: 2025-02-09 23:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads_reports'
down_revision = ('add_user_id_to_reports', 'fix_report_status')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass 