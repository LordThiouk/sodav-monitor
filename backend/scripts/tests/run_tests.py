#!/usr/bin/env python3
"""Script pour exécuter les tests et vérifier le backend."""

import logging
import os
import subprocess
import sys
from typing import List, Tuple

import pytest

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def check_dependencies() -> bool:
    """Vérifie que toutes les dépendances sont installées."""
    try:
        import fastapi
        import librosa
        import numpy
        import pydantic
        import sqlalchemy

        logger.info("✅ Toutes les dépendances sont installées")
        return True
    except ImportError as e:
        logger.error(f"❌ Dépendance manquante: {str(e)}")
        return False


def run_linter() -> Tuple[bool, List[str]]:
    """Exécute le linter sur le code."""
    try:
        import flake8.api.legacy as flake8

        style_guide = flake8.get_style_guide(max_line_length=100, ignore=["E402", "W503"])

        report = style_guide.check_files(["backend"])

        if report.total_errors > 0:
            logger.warning(f"⚠️ {report.total_errors} erreurs de style détectées")
            return False, report.get_statistics("")

        logger.info("✅ Vérification du style de code réussie")
        return True, []

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution du linter: {str(e)}")
        return False, [str(e)]


def run_tests() -> bool:
    """Exécute les tests avec pytest."""
    try:
        # Change le répertoire de travail vers le dossier backend
        os.chdir(os.path.join(os.path.dirname(__file__), "..", "backend"))

        # Exécute les tests
        result = pytest.main(
            [
                "--verbose",
                "--tb=short",
                "--cov=backend",
                "--cov-report=term-missing",
                "--cov-report=html",
                "--asyncio-mode=auto",
                "tests",
            ]
        )

        if result == 0:
            logger.info("✅ Tous les tests ont réussi")
            return True
        else:
            logger.error("❌ Certains tests ont échoué")
            return False

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution des tests: {str(e)}")
        return False


def check_database() -> bool:
    """Vérifie la connexion à la base de données."""
    try:
        from backend.database import engine
        from backend.models import Base

        # Teste la connexion
        with engine.connect() as conn:
            conn.execute("SELECT 1")

        logger.info("✅ Connexion à la base de données réussie")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur de connexion à la base de données: {str(e)}")
        return False


def check_redis() -> bool:
    """Vérifie la connexion à Redis."""
    try:
        import redis

        from backend.config import get_settings

        settings = get_settings()
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
        )

        r.ping()
        logger.info("✅ Connexion à Redis réussie")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur de connexion à Redis: {str(e)}")
        return False


def main():
    """Point d'entrée principal."""
    success = True

    # Vérifie les dépendances
    if not check_dependencies():
        success = False

    # Exécute le linter
    linter_success, linter_errors = run_linter()
    if not linter_success:
        success = False
        for error in linter_errors:
            logger.warning(f"Erreur de style: {error}")

    # Vérifie la base de données
    if not check_database():
        success = False

    # Vérifie Redis
    if not check_redis():
        success = False

    # Exécute les tests
    if not run_tests():
        success = False

    if success:
        logger.info("✅ Toutes les vérifications ont réussi")
        sys.exit(0)
    else:
        logger.error("❌ Certaines vérifications ont échoué")
        sys.exit(1)


if __name__ == "__main__":
    main()
