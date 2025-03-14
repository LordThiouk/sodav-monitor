"""add progress column

Revision ID: 20240321_add_progress
Revises:
Create Date: 2024-03-21

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20240321_add_progress"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add progress column with default value 0.0
    op.add_column(
        "reports", sa.Column("progress", sa.Float(), nullable=False, server_default="0.0")
    )

    # Update existing records based on status
    op.execute(
        """
        UPDATE reports
        SET progress = CASE
            WHEN status = 'completed' THEN 1.0
            WHEN status = 'failed' THEN 0.0
            ELSE 0.0
        END
    """
    )


def downgrade() -> None:
    op.drop_column("reports", "progress")
