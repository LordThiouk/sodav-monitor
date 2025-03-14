"""add missing columns

Revision ID: 20250303_025430
Revises: 20250303_025429
Create Date: 2025-03-03 02:54:30.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250303_025430"
down_revision = "20250303_025429"
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to reports table
    op.add_column("reports", sa.Column("title", sa.String(), nullable=False))
    op.add_column("reports", sa.Column("type", sa.String(), nullable=False))
    op.add_column("reports", sa.Column("report_type", sa.String(), nullable=False))
    op.add_column("reports", sa.Column("format", sa.String(), nullable=False))
    op.add_column(
        "reports", sa.Column("status", sa.String(), nullable=False, server_default="pending")
    )
    op.add_column("reports", sa.Column("progress", sa.Float(), nullable=True, server_default="0.0"))
    op.add_column("reports", sa.Column("parameters", sa.JSON(), nullable=True))
    op.add_column("reports", sa.Column("file_path", sa.String(), nullable=True))
    op.add_column("reports", sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.add_column("reports", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # Add missing columns to report_subscriptions table
    op.add_column("report_subscriptions", sa.Column("format", sa.String(), nullable=False))
    op.add_column("report_subscriptions", sa.Column("parameters", sa.JSON(), nullable=True))
    op.add_column("report_subscriptions", sa.Column("filters", sa.JSON(), nullable=True))
    op.add_column(
        "report_subscriptions",
        sa.Column("include_graphs", sa.Boolean(), nullable=True, server_default="true"),
    )
    op.add_column(
        "report_subscriptions",
        sa.Column("language", sa.String(), nullable=True, server_default="fr"),
    )
    op.add_column(
        "report_subscriptions",
        sa.Column("active", sa.Boolean(), nullable=True, server_default="true"),
    )
    op.add_column("report_subscriptions", sa.Column("updated_at", sa.DateTime(), nullable=True))


def downgrade():
    # Remove columns from reports table
    op.drop_column("reports", "title")
    op.drop_column("reports", "type")
    op.drop_column("reports", "report_type")
    op.drop_column("reports", "format")
    op.drop_column("reports", "status")
    op.drop_column("reports", "progress")
    op.drop_column("reports", "parameters")
    op.drop_column("reports", "file_path")
    op.drop_column("reports", "completed_at")
    op.drop_column("reports", "updated_at")

    # Remove columns from report_subscriptions table
    op.drop_column("report_subscriptions", "format")
    op.drop_column("report_subscriptions", "parameters")
    op.drop_column("report_subscriptions", "filters")
    op.drop_column("report_subscriptions", "include_graphs")
    op.drop_column("report_subscriptions", "language")
    op.drop_column("report_subscriptions", "active")
    op.drop_column("report_subscriptions", "updated_at")
