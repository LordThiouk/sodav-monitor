"""Add missing report columns

Revision ID: 20250303_025432
Revises: 20250303_025431
Create Date: 2025-03-03 02:54:32.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = "20250303_025432"
down_revision = "20250303_025431"
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to reports table
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'reports' AND column_name = 'title'
            ) THEN
                ALTER TABLE reports ADD COLUMN title VARCHAR NOT NULL DEFAULT 'Report';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'reports' AND column_name = 'type'
            ) THEN
                ALTER TABLE reports ADD COLUMN type VARCHAR NOT NULL DEFAULT 'daily';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'reports' AND column_name = 'report_type'
            ) THEN
                ALTER TABLE reports ADD COLUMN report_type VARCHAR NOT NULL DEFAULT 'daily';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'reports' AND column_name = 'format'
            ) THEN
                ALTER TABLE reports ADD COLUMN format VARCHAR NOT NULL DEFAULT 'pdf';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'reports' AND column_name = 'status'
            ) THEN
                ALTER TABLE reports ADD COLUMN status VARCHAR NOT NULL DEFAULT 'pending';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'reports' AND column_name = 'progress'
            ) THEN
                ALTER TABLE reports ADD COLUMN progress FLOAT DEFAULT 0.0;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'reports' AND column_name = 'parameters'
            ) THEN
                ALTER TABLE reports ADD COLUMN parameters JSONB;
            END IF;
        END $$;
    """
    )

    # Add missing columns to report_subscriptions table
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'report_subscriptions' AND column_name = 'format'
            ) THEN
                ALTER TABLE report_subscriptions ADD COLUMN format VARCHAR NOT NULL DEFAULT 'pdf';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'report_subscriptions' AND column_name = 'parameters'
            ) THEN
                ALTER TABLE report_subscriptions ADD COLUMN parameters JSONB;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'report_subscriptions' AND column_name = 'filters'
            ) THEN
                ALTER TABLE report_subscriptions ADD COLUMN filters JSONB;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'report_subscriptions' AND column_name = 'include_graphs'
            ) THEN
                ALTER TABLE report_subscriptions ADD COLUMN include_graphs BOOLEAN DEFAULT true;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'report_subscriptions' AND column_name = 'language'
            ) THEN
                ALTER TABLE report_subscriptions ADD COLUMN language VARCHAR DEFAULT 'fr';
            END IF;
        END $$;
    """
    )


def downgrade():
    # Remove columns from reports table
    op.execute(
        """
        ALTER TABLE reports
        DROP COLUMN IF EXISTS title,
        DROP COLUMN IF EXISTS type,
        DROP COLUMN IF EXISTS report_type,
        DROP COLUMN IF EXISTS format,
        DROP COLUMN IF EXISTS status,
        DROP COLUMN IF EXISTS progress,
        DROP COLUMN IF EXISTS parameters;
    """
    )

    # Remove columns from report_subscriptions table
    op.execute(
        """
        ALTER TABLE report_subscriptions
        DROP COLUMN IF EXISTS format,
        DROP COLUMN IF EXISTS parameters,
        DROP COLUMN IF EXISTS filters,
        DROP COLUMN IF EXISTS include_graphs,
        DROP COLUMN IF EXISTS language;
    """
    )
