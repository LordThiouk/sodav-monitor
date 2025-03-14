#!/usr/bin/env python3
"""Script de réorganisation unifié pour le projet SODAV Monitor.

Ce script combine les fonctionnalités de reorganize.py et reorganize_backend.py,
et ajoute des tests de cohérence des chemins et de la création des dossiers.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pytest

from backend.config import PATHS

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ProjectReorganizer:
    """Classe pour gérer la réorganisation du projet."""

    def __init__(self):
        """Initialise la structure du projet."""
        self.base_dirs = {
            "backend": [
                "analytics",
                "core",
                "detection",
                "logs",
                "models",
                "processing",
                "reports",
                "routers",
                "schemas",
                "tests",
                "utils",
                "data",
                "static",
            ],
            "frontend/src": ["components", "pages", "services", "theme", "utils"],
            "frontend": ["public"],
            "": ["scripts", "docker", "docs"],
        }

        self.file_moves = {
            "backend/detection/": [
                "backend/audio_fingerprint.py",
                "backend/audio_processor.py",
                "backend/detect_music.py",
                "backend/fingerprint.py",
                "backend/fingerprint_generator.py",
                "backend/music_recognition.py",
            ],
            "backend/processing/": [
                "backend/radio_manager.py",
                "backend/stream_processor.py",
                "backend/audio_handler.py",
            ],
            "backend/models/": ["backend/models.py", "backend/database.py"],
            "backend/utils/": [
                "backend/config.py",
                "backend/redis_config.py",
                "backend/logging_config.py",
            ],
            "backend/tests/": ["backend/test_*.py"],
            "docker/": ["Dockerfile", "nginx.conf", "default.conf"],
        }

        # Chemins définis dans config.py
        self.config_paths = PATHS

    def ensure_dir(self, path: str) -> None:
        """Crée un répertoire s'il n'existe pas."""
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"✅ Créé le répertoire {path}")

    def update_init_file(self, directory: str) -> None:
        """Met à jour ou crée le fichier __init__.py dans le répertoire."""
        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w", encoding="utf-8") as f:
                f.write(f'"""Module d\'initialisation pour {os.path.basename(directory)}."""\n')
            logger.info(f"✅ Créé {init_file}")

    def move_file(self, src: str, dest: str) -> None:
        """Déplace un fichier en gérant les erreurs."""
        try:
            if "*" in src:
                # Pour les patterns avec wildcard
                base_dir = os.path.dirname(src)
                pattern = os.path.basename(src)
                for file in os.listdir(base_dir):
                    if file.startswith(pattern.replace("*", "")):
                        src_file = os.path.join(base_dir, file)
                        if os.path.isfile(src_file):
                            dest_file = os.path.join(dest, file)
                            self._move_single_file(src_file, dest_file)
            else:
                # Pour les fichiers spécifiques
                if os.path.exists(src):
                    dest_file = os.path.join(dest, os.path.basename(src))
                    self._move_single_file(src, dest_file)
                else:
                    logger.warning(f"⚠️ Fichier source non trouvé: {src}")
        except Exception as e:
            logger.error(f"❌ Erreur lors du déplacement de {src}: {str(e)}")

    def _move_single_file(self, src: str, dest: str) -> None:
        """Déplace un seul fichier."""
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(src, dest)
        logger.info(f"✅ Déplacé {src} vers {dest}")

    def update_reorganisation_doc(self) -> None:
        """Met à jour le fichier REORGANISATION.md."""
        doc_content = (
            f"\n### {datetime.now().strftime('%Y-%m-%d')} - Réorganisation Unifiée du Projet\n\n"
        )
        doc_content += "#### 1. Structure des Dossiers\n"

        for base_dir, subdirs in self.base_dirs.items():
            if base_dir:
                doc_content += f"\n- **{base_dir}/**\n"
            for subdir in subdirs:
                doc_content += f"  - `{subdir}/`\n"

        doc_content += "\n#### 2. Déplacements de Fichiers\n"
        for dest, files in self.file_moves.items():
            doc_content += f"\n- Vers `{dest}`:\n"
            for file in files:
                doc_content += f"  - `{os.path.basename(file)}`\n"

        doc_content += "\n#### 3. Tests de Cohérence\n"
        doc_content += "- Vérification de la cohérence des chemins avec config.py\n"
        doc_content += "- Validation de la création des dossiers\n"
        doc_content += "- Tests des permissions d'accès\n"

        with open("docs/REORGANISATION.md", "a", encoding="utf-8") as f:
            f.write(doc_content)

        logger.info("✅ Documentation mise à jour")

    def test_path_consistency(self) -> List[str]:
        """Teste la cohérence des chemins."""
        errors = []

        # Vérifie que tous les chemins dans config.py existent
        for path_name, path in self.config_paths.items():
            if not os.path.exists(path):
                errors.append(f"Chemin manquant dans config.py: {path_name} ({path})")

        # Vérifie que les chemins sont cohérents
        backend_path = Path("backend")
        if not backend_path.exists():
            errors.append("Dossier backend manquant")
            return errors

        # Vérifie les permissions
        for path in self.config_paths.values():
            try:
                Path(path).touch()
                os.remove(path)
            except (PermissionError, OSError) as e:
                errors.append(f"Problème de permission pour {path}: {str(e)}")

        return errors

    def reorganize(self) -> None:
        """Exécute la réorganisation complète du projet."""
        logger.info("🚀 Début de la réorganisation du projet")

        # Test de cohérence initial
        errors = self.test_path_consistency()
        if errors:
            for error in errors:
                logger.error(error)
            raise Exception("Tests de cohérence échoués")

        # Création des répertoires
        for base_dir, subdirs in self.base_dirs.items():
            for subdir in subdirs:
                full_path = os.path.join(base_dir, subdir) if base_dir else subdir
                self.ensure_dir(full_path)
                if base_dir == "backend":
                    self.update_init_file(full_path)

        # Déplacement des fichiers
        for dest, files in self.file_moves.items():
            self.ensure_dir(dest)
            for file_pattern in files:
                self.move_file(file_pattern, dest)

        # Mise à jour de la documentation
        self.update_reorganisation_doc()

        # Test de cohérence final
        errors = self.test_path_consistency()
        if errors:
            for error in errors:
                logger.error(error)
            logger.warning("⚠️ Certains tests de cohérence ont échoué après la réorganisation")
        else:
            logger.info("✅ Tests de cohérence réussis")

        logger.info("✅ Réorganisation terminée avec succès!")


def main():
    """Point d'entrée principal."""
    try:
        reorganizer = ProjectReorganizer()
        reorganizer.reorganize()
    except Exception as e:
        logger.error(f"❌ Erreur lors de la réorganisation: {str(e)}")
        raise


if __name__ == "__main__":
    main()
