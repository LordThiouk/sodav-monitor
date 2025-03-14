"""
Script pour visualiser les résultats des tests de détection musicale.

Ce script permet de visualiser les résultats des tests de détection musicale
en générant des graphiques et des tableaux à partir des logs exportés.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.dates import DateFormatter
from tabulate import tabulate

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("visualize_detection_results.log")
    ]
)
logger = logging.getLogger("visualize_detection_results")


def load_logs(log_file: str) -> Dict:
    """
    Charge les logs à partir d'un fichier JSON.
    
    Args:
        log_file: Chemin vers le fichier de logs
        
    Returns:
        Dictionnaire contenant les logs
    """
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
        
        logger.info(f"Logs chargés depuis {log_file}")
        logger.info(f"Nombre d'événements de lecture: {len(logs.get('play_logs', []))}")
        logger.info(f"Nombre de détections: {len(logs.get('detection_logs', []))}")
        
        return logs
    except Exception as e:
        logger.error(f"Erreur lors du chargement des logs: {e}")
        return {"play_logs": [], "detection_logs": []}


def convert_logs_to_dataframes(logs: Dict) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convertit les logs en DataFrames pandas.
    
    Args:
        logs: Dictionnaire contenant les logs
        
    Returns:
        Tuple de DataFrames (play_logs_df, detection_logs_df)
    """
    # Convertir les logs de lecture en DataFrame
    play_logs = logs.get("play_logs", [])
    play_logs_df = pd.DataFrame(play_logs)
    
    # Convertir les logs de détection en DataFrame
    detection_logs = logs.get("detection_logs", [])
    detection_logs_df = pd.DataFrame(detection_logs)
    
    # Convertir les timestamps en datetime
    if not play_logs_df.empty and "timestamp" in play_logs_df.columns:
        play_logs_df["timestamp"] = pd.to_datetime(play_logs_df["timestamp"])
    
    if not detection_logs_df.empty and "timestamp" in detection_logs_df.columns:
        detection_logs_df["timestamp"] = pd.to_datetime(detection_logs_df["timestamp"])
    
    return play_logs_df, detection_logs_df


def calculate_detection_metrics(play_logs_df: pd.DataFrame, detection_logs_df: pd.DataFrame) -> Dict:
    """
    Calcule les métriques de détection à partir des logs.
    
    Args:
        play_logs_df: DataFrame des logs de lecture
        detection_logs_df: DataFrame des logs de détection
        
    Returns:
        Dictionnaire contenant les métriques de détection
    """
    metrics = {}
    
    # Vérifier si les DataFrames sont vides
    if play_logs_df.empty or detection_logs_df.empty:
        logger.warning("Les DataFrames sont vides, impossible de calculer les métriques")
        return metrics
    
    # Nombre total d'événements de lecture et de détections
    total_play_events = len(play_logs_df[play_logs_df["event_type"] == "track_start"])
    total_detections = len(detection_logs_df)
    
    metrics["total_play_events"] = total_play_events
    metrics["total_detections"] = total_detections
    
    # Taux de détection
    if total_play_events > 0:
        metrics["detection_rate"] = total_detections / total_play_events
    else:
        metrics["detection_rate"] = 0
    
    # Confiance moyenne
    if "confidence" in detection_logs_df.columns:
        metrics["avg_confidence"] = detection_logs_df["confidence"].mean()
    else:
        metrics["avg_confidence"] = 0
    
    # Durée totale de lecture
    if "play_duration" in detection_logs_df.columns:
        metrics["total_play_duration"] = detection_logs_df["play_duration"].sum()
    else:
        metrics["total_play_duration"] = 0
    
    # Méthodes de détection utilisées
    if "detection_method" in detection_logs_df.columns:
        detection_methods = detection_logs_df["detection_method"].value_counts().to_dict()
        metrics["detection_methods"] = detection_methods
    else:
        metrics["detection_methods"] = {}
    
    # Stations
    if "station_name" in detection_logs_df.columns:
        stations = detection_logs_df["station_name"].value_counts().to_dict()
        metrics["stations"] = stations
    else:
        metrics["stations"] = {}
    
    # Pistes les plus détectées
    if "track_name" in detection_logs_df.columns:
        top_tracks = detection_logs_df["track_name"].value_counts().head(5).to_dict()
        metrics["top_tracks"] = top_tracks
    else:
        metrics["top_tracks"] = {}
    
    return metrics


def plot_detection_timeline(play_logs_df: pd.DataFrame, detection_logs_df: pd.DataFrame, 
                           output_file: Optional[str] = None):
    """
    Génère un graphique de la chronologie des détections.
    
    Args:
        play_logs_df: DataFrame des logs de lecture
        detection_logs_df: DataFrame des logs de détection
        output_file: Chemin du fichier de sortie (optionnel)
    """
    # Vérifier si les DataFrames sont vides
    if play_logs_df.empty or detection_logs_df.empty:
        logger.warning("Les DataFrames sont vides, impossible de générer le graphique")
        return
    
    # Filtrer les événements de début de piste
    track_starts = play_logs_df[play_logs_df["event_type"] == "track_start"]
    
    # Créer la figure
    plt.figure(figsize=(12, 6))
    
    # Tracer les événements de lecture
    if not track_starts.empty and "timestamp" in track_starts.columns:
        plt.scatter(
            track_starts["timestamp"],
            [0] * len(track_starts),
            marker="o",
            color="blue",
            label="Début de piste",
            alpha=0.7
        )
    
    # Tracer les détections
    if not detection_logs_df.empty and "timestamp" in detection_logs_df.columns:
        plt.scatter(
            detection_logs_df["timestamp"],
            [1] * len(detection_logs_df),
            marker="x",
            color="red",
            label="Détection",
            alpha=0.7
        )
    
    # Configurer le graphique
    plt.yticks([0, 1], ["Lecture", "Détection"])
    plt.xlabel("Temps")
    plt.ylabel("Événement")
    plt.title("Chronologie des Événements de Lecture et de Détection")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Formater l'axe des x
    plt.gca().xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))
    plt.gcf().autofmt_xdate()
    
    # Enregistrer ou afficher le graphique
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        logger.info(f"Graphique enregistré dans {output_file}")
    else:
        plt.tight_layout()
        plt.show()


def plot_detection_methods(detection_logs_df: pd.DataFrame, output_file: Optional[str] = None):
    """
    Génère un graphique des méthodes de détection utilisées.
    
    Args:
        detection_logs_df: DataFrame des logs de détection
        output_file: Chemin du fichier de sortie (optionnel)
    """
    # Vérifier si le DataFrame est vide
    if detection_logs_df.empty or "detection_method" not in detection_logs_df.columns:
        logger.warning("Le DataFrame est vide ou ne contient pas de méthodes de détection")
        return
    
    # Compter les méthodes de détection
    method_counts = detection_logs_df["detection_method"].value_counts()
    
    # Créer la figure
    plt.figure(figsize=(10, 6))
    
    # Tracer le graphique en camembert
    plt.pie(
        method_counts,
        labels=method_counts.index,
        autopct="%1.1f%%",
        startangle=90,
        shadow=True,
        explode=[0.05] * len(method_counts)
    )
    
    # Configurer le graphique
    plt.title("Méthodes de Détection Utilisées")
    plt.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle
    
    # Enregistrer ou afficher le graphique
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        logger.info(f"Graphique enregistré dans {output_file}")
    else:
        plt.tight_layout()
        plt.show()


def plot_detection_by_station(detection_logs_df: pd.DataFrame, output_file: Optional[str] = None):
    """
    Génère un graphique des détections par station.
    
    Args:
        detection_logs_df: DataFrame des logs de détection
        output_file: Chemin du fichier de sortie (optionnel)
    """
    # Vérifier si le DataFrame est vide
    if detection_logs_df.empty or "station_name" not in detection_logs_df.columns:
        logger.warning("Le DataFrame est vide ou ne contient pas de noms de stations")
        return
    
    # Compter les détections par station
    station_counts = detection_logs_df["station_name"].value_counts()
    
    # Créer la figure
    plt.figure(figsize=(10, 6))
    
    # Tracer le graphique en barres
    bars = plt.bar(
        station_counts.index,
        station_counts.values,
        color="skyblue",
        edgecolor="black",
        alpha=0.7
    )
    
    # Ajouter les valeurs au-dessus des barres
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.,
            height,
            f"{int(height)}",
            ha="center",
            va="bottom"
        )
    
    # Configurer le graphique
    plt.xlabel("Station")
    plt.ylabel("Nombre de Détections")
    plt.title("Détections par Station")
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis="y", alpha=0.3)
    
    # Enregistrer ou afficher le graphique
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        logger.info(f"Graphique enregistré dans {output_file}")
    else:
        plt.tight_layout()
        plt.show()


def plot_confidence_distribution(detection_logs_df: pd.DataFrame, output_file: Optional[str] = None):
    """
    Génère un histogramme de la distribution des niveaux de confiance.
    
    Args:
        detection_logs_df: DataFrame des logs de détection
        output_file: Chemin du fichier de sortie (optionnel)
    """
    # Vérifier si le DataFrame est vide
    if detection_logs_df.empty or "confidence" not in detection_logs_df.columns:
        logger.warning("Le DataFrame est vide ou ne contient pas de niveaux de confiance")
        return
    
    # Créer la figure
    plt.figure(figsize=(10, 6))
    
    # Tracer l'histogramme
    plt.hist(
        detection_logs_df["confidence"],
        bins=10,
        range=(0, 1),
        color="green",
        edgecolor="black",
        alpha=0.7
    )
    
    # Configurer le graphique
    plt.xlabel("Niveau de Confiance")
    plt.ylabel("Nombre de Détections")
    plt.title("Distribution des Niveaux de Confiance")
    plt.grid(alpha=0.3)
    
    # Enregistrer ou afficher le graphique
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        logger.info(f"Graphique enregistré dans {output_file}")
    else:
        plt.tight_layout()
        plt.show()


def plot_top_tracks(detection_logs_df: pd.DataFrame, output_file: Optional[str] = None, top_n: int = 5):
    """
    Génère un graphique des pistes les plus détectées.
    
    Args:
        detection_logs_df: DataFrame des logs de détection
        output_file: Chemin du fichier de sortie (optionnel)
        top_n: Nombre de pistes à afficher
    """
    # Vérifier si le DataFrame est vide
    if detection_logs_df.empty or "track_name" not in detection_logs_df.columns:
        logger.warning("Le DataFrame est vide ou ne contient pas de noms de pistes")
        return
    
    # Compter les détections par piste
    track_counts = detection_logs_df["track_name"].value_counts().head(top_n)
    
    # Créer la figure
    plt.figure(figsize=(12, 6))
    
    # Tracer le graphique en barres horizontales
    bars = plt.barh(
        track_counts.index,
        track_counts.values,
        color="salmon",
        edgecolor="black",
        alpha=0.7
    )
    
    # Ajouter les valeurs à côté des barres
    for bar in bars:
        width = bar.get_width()
        plt.text(
            width + 0.1,
            bar.get_y() + bar.get_height() / 2.,
            f"{int(width)}",
            ha="left",
            va="center"
        )
    
    # Configurer le graphique
    plt.xlabel("Nombre de Détections")
    plt.ylabel("Piste")
    plt.title(f"Top {top_n} des Pistes les Plus Détectées")
    plt.grid(axis="x", alpha=0.3)
    
    # Enregistrer ou afficher le graphique
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        logger.info(f"Graphique enregistré dans {output_file}")
    else:
        plt.tight_layout()
        plt.show()


def generate_summary_report(metrics: Dict) -> str:
    """
    Génère un rapport de synthèse à partir des métriques.
    
    Args:
        metrics: Dictionnaire contenant les métriques
        
    Returns:
        Rapport de synthèse au format texte
    """
    report = []
    
    # Titre
    report.append("=== RAPPORT DE SYNTHÈSE DES DÉTECTIONS ===")
    report.append("")
    
    # Statistiques générales
    report.append("--- Statistiques Générales ---")
    report.append(f"Nombre total d'événements de lecture: {metrics.get('total_play_events', 0)}")
    report.append(f"Nombre total de détections: {metrics.get('total_detections', 0)}")
    report.append(f"Taux de détection: {metrics.get('detection_rate', 0):.2%}")
    report.append(f"Confiance moyenne: {metrics.get('avg_confidence', 0):.2f}")
    report.append(f"Durée totale de lecture: {metrics.get('total_play_duration', 0):.2f} secondes")
    report.append("")
    
    # Méthodes de détection
    report.append("--- Méthodes de Détection ---")
    detection_methods = metrics.get("detection_methods", {})
    if detection_methods:
        for method, count in detection_methods.items():
            report.append(f"{method}: {count} détection(s)")
    else:
        report.append("Aucune méthode de détection enregistrée")
    report.append("")
    
    # Stations
    report.append("--- Détections par Station ---")
    stations = metrics.get("stations", {})
    if stations:
        for station, count in stations.items():
            report.append(f"{station}: {count} détection(s)")
    else:
        report.append("Aucune station enregistrée")
    report.append("")
    
    # Pistes les plus détectées
    report.append("--- Top 5 des Pistes les Plus Détectées ---")
    top_tracks = metrics.get("top_tracks", {})
    if top_tracks:
        for track, count in top_tracks.items():
            report.append(f"{track}: {count} détection(s)")
    else:
        report.append("Aucune piste enregistrée")
    
    return "\n".join(report)


def generate_html_report(metrics: Dict, play_logs_df: pd.DataFrame, detection_logs_df: pd.DataFrame,
                        output_dir: str):
    """
    Génère un rapport HTML complet avec graphiques.
    
    Args:
        metrics: Dictionnaire contenant les métriques
        play_logs_df: DataFrame des logs de lecture
        detection_logs_df: DataFrame des logs de détection
        output_dir: Répertoire de sortie pour les fichiers
    """
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Générer les graphiques
    plot_detection_timeline(play_logs_df, detection_logs_df, os.path.join(output_dir, "timeline.png"))
    plot_detection_methods(detection_logs_df, os.path.join(output_dir, "methods.png"))
    plot_detection_by_station(detection_logs_df, os.path.join(output_dir, "stations.png"))
    plot_confidence_distribution(detection_logs_df, os.path.join(output_dir, "confidence.png"))
    plot_top_tracks(detection_logs_df, os.path.join(output_dir, "top_tracks.png"))
    
    # Générer le contenu HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Rapport de Détection Musicale</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                color: #333;
            }}
            h1, h2, h3 {{
                color: #2c3e50;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            .metrics-card {{
                background-color: #f9f9f9;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }}
            .metric-item {{
                background-color: #fff;
                border-radius: 5px;
                padding: 15px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .metric-value {{
                font-size: 24px;
                font-weight: bold;
                color: #3498db;
            }}
            .metric-label {{
                font-size: 14px;
                color: #7f8c8d;
            }}
            .chart-container {{
                background-color: #fff;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .chart-img {{
                width: 100%;
                height: auto;
                max-width: 100%;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .footer {{
                margin-top: 30px;
                text-align: center;
                font-size: 14px;
                color: #7f8c8d;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Rapport de Détection Musicale</h1>
            <p>Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M:%S")}</p>
            
            <h2>Statistiques Générales</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-value">{metrics.get('total_play_events', 0)}</div>
                    <div class="metric-label">Événements de lecture</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{metrics.get('total_detections', 0)}</div>
                    <div class="metric-label">Détections</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{metrics.get('detection_rate', 0):.2%}</div>
                    <div class="metric-label">Taux de détection</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{metrics.get('avg_confidence', 0):.2f}</div>
                    <div class="metric-label">Confiance moyenne</div>
                </div>
                <div class="metric-item">
                    <div class="metric-value">{metrics.get('total_play_duration', 0):.2f}s</div>
                    <div class="metric-label">Durée totale de lecture</div>
                </div>
            </div>
            
            <h2>Chronologie des Événements</h2>
            <div class="chart-container">
                <img src="timeline.png" alt="Chronologie des événements" class="chart-img">
            </div>
            
            <h2>Méthodes de Détection</h2>
            <div class="chart-container">
                <img src="methods.png" alt="Méthodes de détection" class="chart-img">
            </div>
            
            <h2>Détections par Station</h2>
            <div class="chart-container">
                <img src="stations.png" alt="Détections par station" class="chart-img">
            </div>
            
            <h2>Distribution des Niveaux de Confiance</h2>
            <div class="chart-container">
                <img src="confidence.png" alt="Distribution des niveaux de confiance" class="chart-img">
            </div>
            
            <h2>Top des Pistes les Plus Détectées</h2>
            <div class="chart-container">
                <img src="top_tracks.png" alt="Top des pistes les plus détectées" class="chart-img">
            </div>
            
            <h2>Détails des Détections</h2>
            <div class="metrics-card">
                <table>
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Station</th>
                            <th>Piste</th>
                            <th>Méthode</th>
                            <th>Confiance</th>
                            <th>Durée (s)</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Ajouter les détails des détections
    if not detection_logs_df.empty:
        for _, row in detection_logs_df.iterrows():
            timestamp = row.get("timestamp", "")
            station = row.get("station_name", "")
            track = row.get("track_name", "")
            method = row.get("detection_method", "")
            confidence = row.get("confidence", 0)
            duration = row.get("play_duration", 0)
            
            html_content += f"""
                        <tr>
                            <td>{timestamp}</td>
                            <td>{station}</td>
                            <td>{track}</td>
                            <td>{method}</td>
                            <td>{confidence:.2f}</td>
                            <td>{duration:.2f}</td>
                        </tr>
            """
    else:
        html_content += """
                        <tr>
                            <td colspan="6">Aucune détection enregistrée</td>
                        </tr>
        """
    
    # Fermer le tableau et le document HTML
    html_content += """
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p>Rapport généré par le script visualize_detection_results.py</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Écrire le fichier HTML
    html_file = os.path.join(output_dir, "report.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    logger.info(f"Rapport HTML généré dans {html_file}")


def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        Arguments parsés
    """
    parser = argparse.ArgumentParser(description="Visualisation des résultats de détection musicale")
    
    parser.add_argument(
        "log_file",
        help="Fichier de logs JSON à analyser"
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
    # Parser les arguments
    args = parse_arguments()
    
    # Vérifier si le fichier de logs existe
    if not os.path.exists(args.log_file):
        logger.error(f"Le fichier de logs {args.log_file} n'existe pas")
        return
    
    # Charger les logs
    logs = load_logs(args.log_file)
    
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


if __name__ == "__main__":
    main() 