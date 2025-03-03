"""merge heads

Revision ID: 20250303_025426
Revises: 20240321_006, 20250303_025425
Create Date: 2025-03-03 02:54:26.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250303_025426'
down_revision = None
branch_labels = None
depends_on = ('20240321_006', '20250303_025425')


def upgrade():
    pass


def downgrade():
    pass 