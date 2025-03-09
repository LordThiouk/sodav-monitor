"""merge final

Revision ID: 20250303_025429
Revises: 20250303_025428
Create Date: 2025-03-03 02:54:29.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250303_025429'
down_revision = '20250303_025428'
branch_labels = None
depends_on = None


def upgrade():
    # Ensure all tables exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR NOT NULL UNIQUE,
            email VARCHAR NOT NULL UNIQUE,
            password_hash VARCHAR NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            role VARCHAR DEFAULT 'user',
            reset_token VARCHAR,
            reset_token_expires TIMESTAMP
        )
    """)

    op.execute("""
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
        )
    """)

    op.execute("""
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
        )
    """)


def downgrade():
    # Tables will be handled by individual migration downgrades
    pass 