"""
Script pour exécuter la visualisation des résultats de détection musicale.

Ce script permet de lancer facilement la visualisation des résultats de détection
en générant des graphiques et des rapports à partir des logs exportés.
"""

import argparse
import glob
import logging
import os
import sys
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("run_visualize_detection_results.log")
    ]
)
logger = logging.getLogger("run_visualize_detection_results")


def setup_environment():
    """Configure l'environnement pour la visualisation."""
    # Ajouter le répertoire parent au PYTHONPATH
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = current_dir.parent.parent
    
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
        logger.info(f"Ajout de {backend_dir} au PYTHONPATH")
    
    # Vérifier si les dépendances sont installées
    try:
        import matplotlib
        import pandas
        import numpy
        import tabulate
        logger.info("Toutes les dépendances sont installées")
    except ImportError as e:
        logger.error(f"Dépendance manquante: {e}")
        logger.error("Veuillez installer les dépendances requises:")
        logger.error("pip install matplotlib pandas numpy tabulate")
        return False
    
    return True


def find_log_files():
    """
    Trouve les fichiers de logs JSON dans le répertoire courant.
    
    Returns:
        Liste des fichiers de logs trouvés
    """
    # Chercher les fichiers de logs
    log_files = []
    
    # Motifs de recherche pour les fichiers de logs
    patterns = [
        "*.json",
        "multi_station_test_*.json",
        "simple_detection_test_logs.json",
        "detection_logs_*.json"
    ]
    
    # Chercher les fichiers correspondant aux motifs
    for pattern in patterns:
        log_files.extend(glob.glob(pattern))
    
    # Trier les fichiers par date de modification (le plus récent en premier)
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    return log_files


def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        Arguments parsés
    """
    parser = argparse.ArgumentParser(description="Visualisation des résultats de détection musicale")
    
    parser.add_argument(
        "--log-file",
        dest="log_file",
        help="Fichier de logs JSON à analyser (si non spécifié, le fichier le plus récent sera utilisé)"
    )
    
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default="detection_report",
        help="Répertoire de sortie pour les rapports (défaut: detection_report)"
    )
    
    parser.add_argument(
        "--format",
        choices=["text", "html", "both"],
        default="both",
        help="Format du rapport (défaut: both)"
    )
    
    parser.add_argument(
        "--show-plots",
        action="store_true",
        help="Afficher les graphiques à l'écran"
    )
    
    return parser.parse_args()


def main():
    """Fonction principale."""
    # Configurer l'environnement
    if not setup_environment():
        return
    
    # Parser les arguments
    args = parse_arguments()
    
    # Déterminer le fichier de logs à utiliser
    log_file = args.log_file
    
    if not log_file:
        # Chercher les fichiers de logs
        log_files = find_log_files()
        
        if not log_files:
            logger.error("Aucun fichier de logs trouvé")
            logger.error("Veuillez spécifier un fichier de logs avec l'option --log-file")
            return
        
        # Utiliser le fichier le plus récent
        log_file = log_files[0]
        logger.info(f"Utilisation du fichier de logs le plus récent: {log_file}")
    
    # Vérifier si le fichier existe
    if not os.path.exists(log_file):
        logger.error(f"Le fichier de logs {log_file} n'existe pas")
        return
    
    # Importer le module de visualisation
    try:
        from backend.tests.utils.visualize_detection_results import (
            load_logs, convert_logs_to_dataframes, calculate_detection_metrics,
            generate_summary_report, generate_html_report,
            plot_detection_timeline, plot_detection_methods, plot_detection_by_station,
            plot_confidence_distribution, plot_top_tracks
        )
        
        # Charger les logs
        logs = load_logs(log_file)
        
        # Convertir les logs en DataFrames
        play_logs_df, detection_logs_df = convert_logs_to_dataframes(logs)
        
        # Calculer les métriques
        metrics = calculate_detection_metrics(play_logs_df, detection_logs_df)
        
        # Générer le rapport de synthèse
        if args.format in ["text", "both"]:
            report = generate_summary_report(metrics)
            print(report)
            
            # Enregistrer le rapport dans un fichier
            os.makedirs(args.output_dir, exist_ok=True)
            report_file = os.path.join(args.output_dir, "summary_report.txt")
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"Rapport de synthèse enregistré dans {report_file}")
        
        # Générer le rapport HTML
        if args.format in ["html", "both"]:
            generate_html_report(metrics, play_logs_df, detection_logs_df, args.output_dir)
        
        # Afficher les graphiques
        if args.show_plots:
            plot_detection_timeline(play_logs_df, detection_logs_df)
            plot_detection_methods(detection_logs_df)
            plot_detection_by_station(detection_logs_df)
            plot_confidence_distribution(detection_logs_df)
            plot_top_tracks(detection_logs_df)
        
        logger.info("Visualisation terminée avec succès")
        
    except ImportError as e:
        logger.error(f"Erreur lors de l'importation du module: {e}")
        logger.error("Vérifiez que le fichier visualize_detection_results.py existe et est accessible")
        return
    except Exception as e:
        logger.error(f"Erreur lors de la visualisation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return


if __name__ == "__main__":
    main() 