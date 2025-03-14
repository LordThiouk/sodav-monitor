"""Create reports tables

Revision ID: 20250303_025433
Revises: 20250303_025432
Create Date: 2025-03-03 02:54:33.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "20250303_025433"
down_revision = "20250303_025432"
branch_labels = None
depends_on = None


def upgrade():
    # Create reports table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            title VARCHAR NOT NULL,
            type VARCHAR NOT NULL,
            report_type VARCHAR NOT NULL,
            format VARCHAR NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'pending',
            progress FLOAT DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            parameters JSONB,
            user_id INTEGER REFERENCES users(id),
            file_path VARCHAR,
            created_by INTEGER REFERENCES users(id),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    )

    # Create report_subscriptions table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS report_subscriptions (
            id SERIAL PRIMARY KEY,
            name VARCHAR,
            email VARCHAR,
            frequency VARCHAR NOT NULL,
            report_type VARCHAR NOT NULL,
            format VARCHAR NOT NULL,
            parameters JSONB,
            filters JSONB,
            include_graphs BOOLEAN DEFAULT true,
            language VARCHAR DEFAULT 'fr',
            active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER NOT NULL REFERENCES users(id),
            created_by INTEGER REFERENCES users(id),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    )


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS report_subscriptions;
        DROP TABLE IF EXISTS reports;
    """
    )
