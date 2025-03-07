"""Add missing columns to reports and report_subscriptions tables

Revision ID: 20250303_025431
Revises: 20250303_025430
Create Date: 2025-03-03 02:54:31.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '20250303_025431'
down_revision = '20250303_025430'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to reports table if they don't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reports' AND column_name = 'title') THEN
                ALTER TABLE reports ADD COLUMN title VARCHAR NOT NULL DEFAULT 'Report';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reports' AND column_name = 'type') THEN
                ALTER TABLE reports ADD COLUMN type VARCHAR NOT NULL DEFAULT 'daily';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reports' AND column_name = 'report_type') THEN
                ALTER TABLE reports ADD COLUMN report_type VARCHAR NOT NULL DEFAULT 'daily';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reports' AND column_name = 'format') THEN
                ALTER TABLE reports ADD COLUMN format VARCHAR NOT NULL DEFAULT 'pdf';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reports' AND column_name = 'status') THEN
                ALTER TABLE reports ADD COLUMN status VARCHAR NOT NULL DEFAULT 'pending';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reports' AND column_name = 'progress') THEN
                ALTER TABLE reports ADD COLUMN progress FLOAT DEFAULT 0.0;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reports' AND column_name = 'parameters') THEN
                ALTER TABLE reports ADD COLUMN parameters JSONB;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reports' AND column_name = 'file_path') THEN
                ALTER TABLE reports ADD COLUMN file_path VARCHAR;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reports' AND column_name = 'completed_at') THEN
                ALTER TABLE reports ADD COLUMN completed_at TIMESTAMP;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'reports' AND column_name = 'updated_at') THEN
                ALTER TABLE reports ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            END IF;
        END $$;
    """)

    # Add missing columns to report_subscriptions table if they don't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'report_subscriptions' AND column_name = 'format') THEN
                ALTER TABLE report_subscriptions ADD COLUMN format VARCHAR NOT NULL DEFAULT 'pdf';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'report_subscriptions' AND column_name = 'parameters') THEN
                ALTER TABLE report_subscriptions ADD COLUMN parameters JSONB;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'report_subscriptions' AND column_name = 'filters') THEN
                ALTER TABLE report_subscriptions ADD COLUMN filters JSONB;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'report_subscriptions' AND column_name = 'include_graphs') THEN
                ALTER TABLE report_subscriptions ADD COLUMN include_graphs BOOLEAN DEFAULT true;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'report_subscriptions' AND column_name = 'language') THEN
                ALTER TABLE report_subscriptions ADD COLUMN language VARCHAR DEFAULT 'fr';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'report_subscriptions' AND column_name = 'active') THEN
                ALTER TABLE report_subscriptions ADD COLUMN active BOOLEAN DEFAULT true;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'report_subscriptions' AND column_name = 'updated_at') THEN
                ALTER TABLE report_subscriptions ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            END IF;
        END $$;
    """)


def downgrade():
    # Remove columns from reports table
    op.execute("""
        ALTER TABLE reports 
        DROP COLUMN IF EXISTS title,
        DROP COLUMN IF EXISTS type,
        DROP COLUMN IF EXISTS report_type,
        DROP COLUMN IF EXISTS format,
        DROP COLUMN IF EXISTS status,
        DROP COLUMN IF EXISTS progress,
        DROP COLUMN IF EXISTS parameters,
        DROP COLUMN IF EXISTS file_path,
        DROP COLUMN IF EXISTS completed_at,
        DROP COLUMN IF EXISTS updated_at;
    """)

    # Remove columns from report_subscriptions table
    op.execute("""
        ALTER TABLE report_subscriptions
        DROP COLUMN IF EXISTS format,
        DROP COLUMN IF EXISTS parameters,
        DROP COLUMN IF EXISTS filters,
        DROP COLUMN IF EXISTS include_graphs,
        DROP COLUMN IF EXISTS language,
        DROP COLUMN IF EXISTS active,
        DROP COLUMN IF EXISTS updated_at;
    """) 