"""Script pour exécuter les migrations de la base de données"""
import os
import sys
from alembic import command
from alembic.config import Config

def run_migrations():
    try:
        # Obtenir le chemin du fichier alembic.ini
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
        
        # Définir le chemin des scripts de migration
        alembic_cfg.set_main_option("script_location", os.path.dirname(__file__))
        
        # Exécuter la migration
        command.upgrade(alembic_cfg, "head")
        print("✅ Migration completed successfully")
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations() 