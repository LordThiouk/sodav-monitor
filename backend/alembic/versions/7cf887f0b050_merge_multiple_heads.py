"""merge_multiple_heads

Revision ID: 7cf887f0b050
Revises: c7dbabca2edd, merge_heads_fingerprint
Create Date: 2025-02-10 05:07:46.179661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7cf887f0b050'
down_revision: Union[str, None] = ('c7dbabca2edd', 'merge_heads_fingerprint')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
