"""add_user_id_to_report_subscriptions_only

Revision ID: 1551b39f5d76
Revises: merge_heads_reports
Create Date: 2025-02-10 01:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1551b39f5d76'
down_revision: Union[str, None] = 'merge_heads_reports'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column to report_subscriptions table
    with op.batch_alter_table('report_subscriptions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_report_subscriptions_user_id',
            'users',
            ['user_id'],
            ['id']
        )
        # Update existing rows to have a default user_id (1)
        op.execute('UPDATE report_subscriptions SET user_id = 1')
        # Now make the column not nullable
        batch_op.alter_column('user_id', nullable=False)


def downgrade() -> None:
    # Remove user_id column from report_subscriptions table
    with op.batch_alter_table('report_subscriptions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_report_subscriptions_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')
