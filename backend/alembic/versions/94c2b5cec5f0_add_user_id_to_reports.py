"""add_user_id_to_reports

Revision ID: 94c2b5cec5f0
Revises: 78075365df55
Create Date: 2025-02-09 23:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94c2b5cec5f0'
down_revision: Union[str, None] = '78075365df55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column to reports table
    with op.batch_alter_table('reports') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_reports_user_id',
            'users',
            ['user_id'],
            ['id']
        )


def downgrade() -> None:
    # Remove user_id column from reports table
    with op.batch_alter_table('reports') as batch_op:
        batch_op.drop_constraint('fk_reports_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')
