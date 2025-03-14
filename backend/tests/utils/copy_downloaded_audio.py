"""
Script pour copier des fichiers audio depuis le dossier Téléchargements.

Ce script permet de copier facilement des fichiers audio depuis le dossier Téléchargements
vers le répertoire de test pour les utiliser dans les tests de détection musicale.
"""

import logging
import os
import shutil
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("copy_downloaded_audio")

# Extensions de fichiers audio supportées
SUPPORTED_EXTENSIONS = [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"]


def get_downloads_folder():
    """Retourne le chemin vers le dossier Téléchargements de l'utilisateur."""
    # Essayer de trouver le dossier Téléchargements selon le système d'exploitation
    if os.name == "nt":  # Windows
        # Essayer d'abord le chemin standard
        downloads = Path.home() / "Downloads"
        if downloads.exists():
            return downloads
        
        # Essayer le chemin en français
        downloads = Path.home() / "Téléchargements"
        if downloads.exists():
            return downloads
        
        # Essayer de lire depuis le registre Windows
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                downloads = Path(winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0])
                if downloads.exists():
                    return downloads
        except Exception:
            pass
    else:  # macOS, Linux, etc.
        downloads = Path.home() / "Downloads"
        if downloads.exists():
            return downloads
    
    # Demander à l'utilisateur si le chemin n'a pas été trouvé
    while True:
        path = input("Entrez le chemin vers votre dossier Téléchargements: ").strip()
        downloads = Path(path)
        if downloads.exists() and downloads.is_dir():
            return downloads
        logger.error(f"Le chemin '{path}' n'existe pas ou n'est pas un dossier. Veuillez réessayer.")


def get_target_folder():
    """Retourne le chemin vers le dossier cible pour les fichiers audio."""
    # Répertoire des fichiers audio pour les tests
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    audio_dir = script_dir.parent / "data" / "audio" / "senegal"
    
    # Créer le répertoire s'il n'existe pas
    audio_dir.parent.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(exist_ok=True)
    
    return audio_dir


def list_audio_files(directory):
    """Liste tous les fichiers audio dans le répertoire spécifié."""
    audio_files = []
    
    for ext in SUPPORTED_EXTENSIONS:
        audio_files.extend(directory.glob(f"*{ext}"))
    
    return audio_files


def copy_audio_files():
    """
    Copie les fichiers audio depuis le dossier Téléchargements vers le répertoire de test.
    
    Returns:
        int: Nombre de fichiers copiés
    """
    # Obtenir les chemins des dossiers
    downloads_folder = get_downloads_folder()
    target_folder = get_target_folder()
    
    logger.info(f"Recherche de fichiers audio dans {downloads_folder}")
    
    # Lister les fichiers audio dans le dossier Téléchargements
    audio_files = list_audio_files(downloads_folder)
    
    if not audio_files:
        logger.warning(f"Aucun fichier audio trouvé dans {downloads_folder}")
        return 0
    
    logger.info(f"{len(audio_files)} fichiers audio trouvés")
    
    # Afficher les fichiers trouvés
    for i, file in enumerate(audio_files):
        logger.info(f"{i+1}. {file.name} ({file.stat().st_size / (1024*1024):.2f} MB)")
    
    # Demander à l'utilisateur quels fichiers copier
    while True:
        selection = input(
            "Entrez les numéros des fichiers à copier (séparés par des virgules), "
            "'all' pour tous, ou 'q' pour quitter: "
        ).strip().lower()
        
        if selection == "q":
            return 0
        
        if selection == "all":
            selected_indices = list(range(len(audio_files)))
            break
        
        try:
            # Convertir les indices en base 0
            selected_indices = [int(idx.strip()) - 1 for idx in selection.split(",")]
            
            # Vérifier que les indices sont valides
            if all(0 <= idx < len(audio_files) for idx in selected_indices):
                break
            else:
                logger.error("Certains indices sont hors limites. Veuillez réessayer.")
        except ValueError:
            logger.error("Format invalide. Veuillez entrer des numéros séparés par des virgules.")
    
    # Copier les fichiers sélectionnés
    copied_count = 0
    
    for idx in selected_indices:
        source_file = audio_files[idx]
        target_file = target_folder / source_file.name
        
        try:
            logger.info(f"Copie de {source_file.name}...")
            shutil.copy2(source_file, target_file)
            logger.info(f"Fichier copié avec succès: {target_file}")
            copied_count += 1
        except Exception as e:
            logger.error(f"Erreur lors de la copie de {source_file.name}: {e}")
    
    logger.info(f"{copied_count} fichiers copiés avec succès vers {target_folder}")
    return copied_count


if __name__ == "__main__":
    # Exécuter la copie des fichiers
    copy_audio_files() 