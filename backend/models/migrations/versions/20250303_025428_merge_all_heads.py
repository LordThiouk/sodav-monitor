"""merge all heads

Revision ID: 20250303_025428
Revises: 20240321_005, 20250303_025426, 20250303_025427, e86d43af3950
Create Date: 2025-03-03 02:54:28.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250303_025428"
down_revision = None
depends_on = ("20240321_005", "20250303_025426", "20250303_025427", "e86d43af3950")
branch_labels = None


def upgrade():
    pass


def downgrade():
    pass
