"""Add isrc, label, and album columns to tracks table

Revision ID: 20240321_005
Revises: 20240321_004_merge_heads
Create Date: 2024-03-21 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20240321_005"
down_revision = "20240321_004_merge_heads"
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to tracks table
    op.add_column("tracks", sa.Column("isrc", sa.String(length=12), nullable=True))
    op.add_column("tracks", sa.Column("label", sa.String(length=255), nullable=True))
    op.add_column("tracks", sa.Column("album", sa.String(length=255), nullable=True))


def downgrade():
    # Remove columns from tracks table
    op.drop_column("tracks", "album")
    op.drop_column("tracks", "label")
    op.drop_column("tracks", "isrc")
