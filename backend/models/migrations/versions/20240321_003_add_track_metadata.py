"""Add metadata columns to tracks table

Revision ID: 20240321_003_add_track_metadata
Revises: 20240321_002_add_reset_token
Create Date: 2024-03-02 22:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20240321_003_add_track_metadata"
down_revision = "20240321_002_add_reset_token"
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to tracks table
    op.add_column("tracks", sa.Column("isrc", sa.String(length=12), nullable=True))
    op.add_column("tracks", sa.Column("label", sa.String(length=255), nullable=True))
    op.add_column("tracks", sa.Column("album", sa.String(length=255), nullable=True))

    # Add index on isrc for faster lookups
    op.create_index(op.f("ix_tracks_isrc"), "tracks", ["isrc"], unique=False)


def downgrade():
    # Remove index first
    op.drop_index(op.f("ix_tracks_isrc"), table_name="tracks")

    # Remove columns
    op.drop_column("tracks", "album")
    op.drop_column("tracks", "label")
    op.drop_column("tracks", "isrc")
