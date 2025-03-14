from alembic import op
from sqlalchemy import text


def upgrade():
    # Add unique constraint to hour column in detection_hourly table
    op.execute(
        text(
            """
        ALTER TABLE detection_hourly ADD CONSTRAINT detection_hourly_hour_key UNIQUE (hour);
    """
        )
    )


def downgrade():
    # Remove unique constraint from hour column in detection_hourly table
    op.execute(
        text(
            """
        ALTER TABLE detection_hourly DROP CONSTRAINT IF EXISTS detection_hourly_hour_key;
    """
        )
    )
