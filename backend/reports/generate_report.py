from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy.orm import Session
from ..analytics.stats_manager import StatsManager
import logging
import os
from fpdf import FPDF
import json

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.stats_manager = StatsManager(db_session)
        self.report_dir = "reports"
        os.makedirs(self.report_dir, exist_ok=True)

    async def generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "pdf",
        include_stats: bool = True
    ) -> str:
        """
        Génère un rapport dans le format spécifié (pdf, xlsx, csv)
        """
        try:
            # Récupérer les statistiques
            daily_stats = []
            current_date = start_date
            while current_date <= end_date:
                stats = await self.stats_manager.generate_daily_report(current_date)
                daily_stats.append(stats)
                current_date += timedelta(days=1)

            # Générer le rapport dans le format demandé
            if format.lower() == "pdf":
                return await self._generate_pdf_report(daily_stats, start_date, end_date)
            elif format.lower() == "xlsx":
                return await self._generate_excel_report(daily_stats, start_date, end_date)
            elif format.lower() == "csv":
                return await self._generate_csv_report(daily_stats, start_date, end_date)
            else:
                raise ValueError(f"Format de rapport non supporté : {format}")

        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport : {str(e)}")
            raise

    async def _generate_pdf_report(
        self,
        daily_stats: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """
        Génère un rapport PDF détaillé
        """
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # En-tête
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "Rapport de Diffusion SODAV", ln=True, align="C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Période : {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}", ln=True, align="C")
            
            # Statistiques globales
            total_detections = sum(stats["total_detections"] for stats in daily_stats)
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Statistiques Globales", ln=True)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Total des détections : {total_detections}", ln=True)
            
            # Top morceaux
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Top Morceaux", ln=True)
            pdf.set_font("Arial", "", 12)
            for stats in daily_stats:
                for track in stats["top_tracks"][:5]:  # Top 5 par jour
                    pdf.cell(0, 10, f"{track['title']} - {track['artist']} ({track['detections']} détections)", ln=True)
            
            # Top artistes
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Top Artistes", ln=True)
            pdf.set_font("Arial", "", 12)
            for stats in daily_stats:
                for artist in stats["top_artists"][:5]:  # Top 5 par jour
                    pdf.cell(0, 10, f"{artist['name']} ({artist['detections']} détections)", ln=True)
            
            # Statistiques par station
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Statistiques par Station", ln=True)
            pdf.set_font("Arial", "", 12)
            for stats in daily_stats:
                for station in stats["station_stats"]:
                    pdf.cell(0, 10, f"{station['name']}: {station['detections']} détections", ln=True)
            
            # Sauvegarder le PDF
            filename = f"report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
            filepath = os.path.join(self.report_dir, filename)
            pdf.output(filepath)
            
            return filepath

        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport PDF : {str(e)}")
            raise

    async def _generate_excel_report(
        self,
        daily_stats: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """
        Génère un rapport Excel avec plusieurs feuilles
        """
        try:
            filename = f"report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
            filepath = os.path.join(self.report_dir, filename)
            
            # Créer un writer Excel
            with pd.ExcelWriter(filepath) as writer:
                # Feuille des statistiques globales
                global_stats = pd.DataFrame([{
                    "Date": stats["date"],
                    "Détections": stats["total_detections"],
                    "Temps de Jeu": stats["total_play_time"]
                } for stats in daily_stats])
                global_stats.to_excel(writer, sheet_name="Statistiques Globales", index=False)
                
                # Feuille des top morceaux
                tracks_data = []
                for stats in daily_stats:
                    for track in stats["top_tracks"]:
                        tracks_data.append({
                            "Date": stats["date"],
                            "Titre": track["title"],
                            "Artiste": track["artist"],
                            "Détections": track["detections"],
                            "Temps de Jeu": track["play_time"]
                        })
                pd.DataFrame(tracks_data).to_excel(writer, sheet_name="Top Morceaux", index=False)
                
                # Feuille des top artistes
                artists_data = []
                for stats in daily_stats:
                    for artist in stats["top_artists"]:
                        artists_data.append({
                            "Date": stats["date"],
                            "Artiste": artist["name"],
                            "Détections": artist["detections"],
                            "Temps de Jeu": artist["play_time"]
                        })
                pd.DataFrame(artists_data).to_excel(writer, sheet_name="Top Artistes", index=False)
                
                # Feuille des statistiques par station
                stations_data = []
                for stats in daily_stats:
                    for station in stats["station_stats"]:
                        stations_data.append({
                            "Date": stats["date"],
                            "Station": station["name"],
                            "Détections": station["detections"],
                            "Temps de Jeu": station["play_time"]
                        })
                pd.DataFrame(stations_data).to_excel(writer, sheet_name="Statistiques Stations", index=False)
            
            return filepath

        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport Excel : {str(e)}")
            raise

    async def _generate_csv_report(
        self,
        daily_stats: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """
        Génère un rapport CSV
        """
        try:
            filename = f"report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
            filepath = os.path.join(self.report_dir, filename)
            
            # Préparer les données
            report_data = []
            for stats in daily_stats:
                # Statistiques globales
                base_row = {
                    "Date": stats["date"],
                    "Total_Detections": stats["total_detections"],
                    "Total_Play_Time": stats["total_play_time"]
                }
                
                # Ajouter les détails des morceaux
                for track in stats["top_tracks"]:
                    row = base_row.copy()
                    row.update({
                        "Type": "Track",
                        "Title": track["title"],
                        "Artist": track["artist"],
                        "Detections": track["detections"],
                        "Play_Time": track["play_time"]
                    })
                    report_data.append(row)
                
                # Ajouter les détails des stations
                for station in stats["station_stats"]:
                    row = base_row.copy()
                    row.update({
                        "Type": "Station",
                        "Name": station["name"],
                        "Detections": station["detections"],
                        "Play_Time": station["play_time"]
                    })
                    report_data.append(row)
            
            # Créer et sauvegarder le DataFrame
            pd.DataFrame(report_data).to_csv(filepath, index=False)
            
            return filepath

        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport CSV : {str(e)}")
            raise 