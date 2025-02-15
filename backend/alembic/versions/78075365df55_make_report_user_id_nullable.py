"""make_report_user_id_nullable

Revision ID: 78075365df55
Revises: add_reports_tables
Create Date: 2025-02-09 22:35:50.129691

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78075365df55'
down_revision: Union[str, None] = 'add_reports_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
