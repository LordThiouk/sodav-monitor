"""add user_id to reports

Revision ID: add_user_id_to_reports
Revises: 78075365df55
Create Date: 2025-02-09 23:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_user_id_to_reports'
down_revision = '78075365df55'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add user_id column to reports table
    op.add_column('reports', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_reports_user_id',
        'reports',
        'users',
        ['user_id'],
        ['id']
    )

def downgrade() -> None:
    # Remove user_id column from reports table
    op.drop_constraint('fk_reports_user_id', 'reports', type_='foreignkey')
    op.drop_column('reports', 'user_id') 