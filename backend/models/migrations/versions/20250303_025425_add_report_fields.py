"""Add report_type and filters fields

Revision ID: 20250303_025425
Revises: 20240321_006
Create Date: 2025-03-03 02:54:25.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250303_025425"
down_revision = "20240321_006"
branch_labels = None
depends_on = None


def upgrade():
    # Add report_type column to reports table
    op.add_column(
        "reports", sa.Column("report_type", sa.String(), nullable=False, server_default="daily")
    )

    # Add filters column to report_subscriptions table
    op.add_column("report_subscriptions", sa.Column("filters", sa.JSON(), nullable=True))


def downgrade():
    # Remove columns
    op.drop_column("reports", "report_type")
    op.drop_column("report_subscriptions", "filters")
