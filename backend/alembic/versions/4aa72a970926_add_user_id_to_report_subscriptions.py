"""add_user_id_to_report_subscriptions

Revision ID: 4aa72a970926
Revises: merge_heads_reports
Create Date: 2025-02-10 01:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4aa72a970926'
down_revision = 'merge_heads_reports'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add user_id column to report_subscriptions table
    with op.batch_alter_table('report_subscriptions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))

    # Update existing rows to have a default user_id (1)
    op.execute('UPDATE report_subscriptions SET user_id = 1')

    # Add foreign key and make column not nullable
    with op.batch_alter_table('report_subscriptions', schema=None) as batch_op:
        batch_op.alter_column('user_id', nullable=False)
        batch_op.create_foreign_key(
            'fk_report_subscriptions_user_id',
            'users',
            ['user_id'],
            ['id']
        )

def downgrade() -> None:
    # Remove user_id column from report_subscriptions table
    with op.batch_alter_table('report_subscriptions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_report_subscriptions_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')
