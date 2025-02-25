"""Initial migration

Revision ID: 3ca146e9a158
Revises: combined_migration
Create Date: 2024-02-16 05:07:29.629453

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '3ca146e9a158'
down_revision = 'combined_migration'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    
    # Check if the enum type already exists
    res = conn.execute(text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'stationstatus')"))
    enum_exists = res.scalar()
    
    if not enum_exists:
        op.execute(text("CREATE TYPE stationstatus AS ENUM ('active', 'inactive')"))
    
    # Check if the table already exists
    res = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'radio_stations')"))
    table_exists = res.scalar()
    
    if not table_exists:
        # Create radio_stations table
        op.create_table('radio_stations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('url', sa.String(length=200), nullable=False),
            sa.Column('status', postgresql.ENUM('active', 'inactive', name='stationstatus', create_type=False), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    conn = op.get_bind()
    
    # Check if the table exists before dropping
    res = conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'radio_stations')"))
    table_exists = res.scalar()
    
    if table_exists:
        op.drop_table('radio_stations')
    
    # Check if the enum type exists before dropping
    res = conn.execute(text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'stationstatus')"))
    enum_exists = res.scalar()
    
    if enum_exists:
        op.execute(text('DROP TYPE stationstatus'))
