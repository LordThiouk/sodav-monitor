"""Add unique constraint to ISRC column in tracks table

Revision ID: 20250303_025434
Revises: 20240321_006_merge_heads
Create Date: 2025-03-03 02:54:34.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250303_025434"
down_revision = "20240321_006_merge_heads"
branch_labels = None
depends_on = None


def upgrade():
    # Nettoyer les doublons d'ISRC avant d'ajouter la contrainte
    op.execute(
        """
        -- Créer une table temporaire pour stocker les ISRC uniques avec l'ID de piste le plus récent
        CREATE TEMPORARY TABLE unique_isrcs AS
        SELECT DISTINCT ON (isrc) isrc, id, created_at
        FROM tracks
        WHERE isrc IS NOT NULL
        ORDER BY isrc, created_at DESC;

        -- Mettre à NULL les ISRC des pistes qui sont des doublons
        UPDATE tracks
        SET isrc = NULL
        WHERE isrc IS NOT NULL
        AND id NOT IN (SELECT id FROM unique_isrcs);
    """
    )

    # Supprimer l'index existant sur isrc
    op.drop_index("ix_tracks_isrc", table_name="tracks")

    # Ajouter la contrainte d'unicité sur la colonne isrc
    op.create_index("ix_tracks_isrc", "tracks", ["isrc"], unique=True)


def downgrade():
    # Supprimer la contrainte d'unicité
    op.drop_index("ix_tracks_isrc", table_name="tracks")

    # Recréer l'index non-unique
    op.create_index("ix_tracks_isrc", "tracks", ["isrc"], unique=False)
