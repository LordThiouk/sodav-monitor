"""merge_heads_final

Revision ID: c7dbabca2edd
Revises: 1551b39f5d76, 4aa72a970926
Create Date: 2025-02-10 01:52:12.630916

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7dbabca2edd'
down_revision: Union[str, None] = ('1551b39f5d76', '4aa72a970926')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
