"""add_hour_constraint

Revision ID: e86d43af3950
Revises: 20240321_001_merge
Create Date: 2025-02-21 17:28:33.758210

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e86d43af3950'
down_revision: Union[str, None] = '20240321_001_merge'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
