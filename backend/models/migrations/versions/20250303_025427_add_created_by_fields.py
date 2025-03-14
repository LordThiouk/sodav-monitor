"""Add created_by fields

Revision ID: 20250303_025427
Revises: 20250303_025425
Create Date: 2025-03-03 02:54:27.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250303_025427"
down_revision = "20250303_025425"
branch_labels = None
depends_on = None


def upgrade():
    # Add created_by and updated_at columns to reports table
    op.add_column("reports", sa.Column("created_by", sa.Integer(), nullable=True))
    op.add_column("reports", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.create_foreign_key(None, "reports", "users", ["created_by"], ["id"])

    # Add created_by and updated_at columns to report_subscriptions table
    op.add_column("report_subscriptions", sa.Column("created_by", sa.Integer(), nullable=True))
    op.add_column("report_subscriptions", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.create_foreign_key(None, "report_subscriptions", "users", ["created_by"], ["id"])


def downgrade():
    # Remove foreign key constraints first
    op.drop_constraint(None, "report_subscriptions", type_="foreignkey")
    op.drop_constraint(None, "reports", type_="foreignkey")

    # Remove columns
    op.drop_column("report_subscriptions", "updated_at")
    op.drop_column("report_subscriptions", "created_by")
    op.drop_column("reports", "updated_at")
    op.drop_column("reports", "created_by")
