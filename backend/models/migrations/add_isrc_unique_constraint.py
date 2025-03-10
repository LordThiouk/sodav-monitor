"""
Script pour ajouter une contrainte d'unicité sur la colonne ISRC de la table tracks.
Ce script nettoie d'abord les doublons d'ISRC avant d'ajouter la contrainte.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, backend_dir)

# Charger les variables d'environnement
load_dotenv()

def add_isrc_unique_constraint():
    """Ajoute une contrainte d'unicité sur la colonne ISRC de la table tracks."""
    try:
        # Récupérer l'URL de la base de données
        db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost/sodav_dev')
        
        # Créer le moteur SQLAlchemy
        engine = create_engine(db_url)
        
        # Nettoyer les doublons d'ISRC avant d'ajouter la contrainte
        with engine.connect() as conn:
            logger.info("Nettoyage des doublons d'ISRC...")
            
            # Créer une table temporaire pour stocker les ISRC uniques avec l'ID de piste le plus récent
            conn.execute(text("""
                CREATE TEMPORARY TABLE unique_isrcs AS
                SELECT DISTINCT ON (isrc) isrc, id, created_at
                FROM tracks
                WHERE isrc IS NOT NULL
                ORDER BY isrc, created_at DESC;
            """))
            
            # Mettre à NULL les ISRC des pistes qui sont des doublons
            result = conn.execute(text("""
                UPDATE tracks
                SET isrc = NULL
                WHERE isrc IS NOT NULL
                AND id NOT IN (SELECT id FROM unique_isrcs);
            """))
            
            logger.info(f"Nombre de doublons nettoyés: {result.rowcount}")
            
            # Vérifier si l'index existe déjà
            index_exists = conn.execute(text("""
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'ix_tracks_isrc';
            """)).fetchone()
            
            if index_exists:
                logger.info("Suppression de l'index existant sur isrc...")
                conn.execute(text("DROP INDEX ix_tracks_isrc;"))
            
            # Ajouter la contrainte d'unicité sur la colonne isrc
            logger.info("Ajout de la contrainte d'unicité sur la colonne isrc...")
            conn.execute(text("""
                CREATE UNIQUE INDEX ix_tracks_isrc ON tracks (isrc)
                WHERE isrc IS NOT NULL;
            """))
            
            conn.commit()
            
        logger.info("✅ Contrainte d'unicité ajoutée avec succès sur la colonne ISRC")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'ajout de la contrainte d'unicité: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    add_isrc_unique_constraint() 