#!/usr/bin/env python
"""
Script pour rechercher et fusionner les pistes dupliquées basées sur l'ISRC.

Ce script identifie les pistes ayant le même code ISRC, sélectionne la piste la plus complète
comme piste principale, et fusionne les données des autres pistes (statistiques, détections, etc.)
vers la piste principale avant de supprimer les doublons.
"""

import os
import sys
import argparse
import logging
from typing import List, Dict, Tuple, Set
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, update, delete
from sqlalchemy.exc import SQLAlchemyError

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, backend_dir)

from backend.models.database import get_db
from backend.models.models import (
    Track, TrackDetection, TrackStats, StationTrackStats,
    Fingerprint, TrackDaily, TrackMonthly
)
from backend.utils.validators import validate_isrc
from backend.logs.log_manager import LogManager

# Configurer le logging
log_manager = LogManager()
logger = log_manager.get_logger("merge_duplicate_isrc")

def find_duplicate_isrc(db_session: Session) -> Dict[str, List[Track]]:
    """
    Trouve les pistes ayant le même code ISRC.
    
    Args:
        db_session: Session de base de données
        
    Returns:
        Dictionnaire avec l'ISRC comme clé et la liste des pistes comme valeur
    """
    # Trouver les ISRC qui apparaissent plus d'une fois
    duplicate_isrc_query = (
        db_session.query(Track.isrc, func.count(Track.id).label('count'))
        .filter(Track.isrc.isnot(None))
        .group_by(Track.isrc)
        .having(func.count(Track.id) > 1)
    )
    
    duplicate_isrc = {row.isrc: [] for row in duplicate_isrc_query.all()}
    
    # Pour chaque ISRC dupliqué, récupérer toutes les pistes correspondantes
    for isrc in duplicate_isrc.keys():
        tracks = db_session.query(Track).filter(Track.isrc == isrc).all()
        duplicate_isrc[isrc] = tracks
    
    return duplicate_isrc

def select_primary_track(tracks: List[Track]) -> Track:
    """
    Sélectionne la piste principale parmi les doublons.
    
    La piste principale est celle qui a le plus d'informations complètes.
    
    Args:
        tracks: Liste des pistes avec le même ISRC
        
    Returns:
        La piste sélectionnée comme principale
    """
    if not tracks:
        raise ValueError("La liste de pistes est vide")
    
    if len(tracks) == 1:
        return tracks[0]
    
    # Système de points pour évaluer la complétude des pistes
    track_scores = []
    
    for track in tracks:
        score = 0
        
        # Points pour les champs non nuls
        if track.title:
            score += 1
        if track.artist_id:
            score += 2
        if track.album:
            score += 1
        if track.label:
            score += 1
        if track.release_date:
            score += 1
        if track.fingerprint:
            score += 3
        if track.fingerprint_raw:
            score += 2
        if track.chromaprint:
            score += 2
        
        # Points pour les statistiques
        if track.stats:
            score += track.stats.total_plays * 0.5
        
        # Points pour les détections
        detection_count = len(track.detections) if track.detections else 0
        score += detection_count * 0.3
        
        # Points pour l'ancienneté (préférer les pistes plus anciennes)
        if track.created_at:
            # Convertir la date en timestamp pour avoir un nombre
            import time
            created_timestamp = time.mktime(track.created_at.timetuple())
            # Inverser pour que les pistes plus anciennes aient un score plus élevé
            score += 1 / (created_timestamp + 1) * 1000
        
        track_scores.append((track, score))
    
    # Trier par score décroissant
    track_scores.sort(key=lambda x: x[1], reverse=True)
    
    primary_track = track_scores[0][0]
    logger.info(f"Piste principale sélectionnée: ID={primary_track.id}, Titre={primary_track.title}, Score={track_scores[0][1]}")
    
    return primary_track

def merge_track_detections(db_session: Session, primary_track_id: int, secondary_track_ids: List[int]) -> int:
    """
    Fusionne les détections des pistes secondaires vers la piste principale.
    
    Args:
        db_session: Session de base de données
        primary_track_id: ID de la piste principale
        secondary_track_ids: Liste des IDs des pistes secondaires
        
    Returns:
        Nombre de détections migrées
    """
    try:
        # Mettre à jour les détections pour qu'elles pointent vers la piste principale
        stmt = update(TrackDetection).where(
            TrackDetection.track_id.in_(secondary_track_ids)
        ).values(track_id=primary_track_id)
        
        result = db_session.execute(stmt)
        return result.rowcount
    except SQLAlchemyError as e:
        logger.error(f"Erreur lors de la fusion des détections: {e}")
        db_session.rollback()
        return 0

def merge_track_stats(db_session: Session, primary_track_id: int, secondary_track_ids: List[int]) -> bool:
    """
    Fusionne les statistiques des pistes secondaires vers la piste principale.
    
    Args:
        db_session: Session de base de données
        primary_track_id: ID de la piste principale
        secondary_track_ids: Liste des IDs des pistes secondaires
        
    Returns:
        True si la fusion a réussi, False sinon
    """
    try:
        # Récupérer les statistiques de la piste principale
        primary_stats = db_session.query(TrackStats).filter(TrackStats.track_id == primary_track_id).first()
        
        if not primary_stats:
            # Créer des statistiques pour la piste principale si elles n'existent pas
            primary_stats = TrackStats(track_id=primary_track_id)
            db_session.add(primary_stats)
            db_session.flush()
        
        # Récupérer les statistiques des pistes secondaires
        secondary_stats = db_session.query(TrackStats).filter(TrackStats.track_id.in_(secondary_track_ids)).all()
        
        # Fusionner les statistiques
        for stats in secondary_stats:
            primary_stats.total_plays += stats.total_plays
            
            # Fusionner le temps de lecture total
            if stats.total_play_time:
                if primary_stats.total_play_time:
                    primary_stats.total_play_time += stats.total_play_time
                else:
                    primary_stats.total_play_time = stats.total_play_time
            
            # Mettre à jour la dernière détection si celle de la piste secondaire est plus récente
            if stats.last_detected and (not primary_stats.last_detected or stats.last_detected > primary_stats.last_detected):
                primary_stats.last_detected = stats.last_detected
            
            # Recalculer la confiance moyenne
            if primary_stats.total_plays > 0:
                primary_stats.average_confidence = (
                    (primary_stats.average_confidence * (primary_stats.total_plays - stats.total_plays) +
                     stats.average_confidence * stats.total_plays) /
                    primary_stats.total_plays
                )
        
        # Supprimer les statistiques des pistes secondaires
        db_session.query(TrackStats).filter(TrackStats.track_id.in_(secondary_track_ids)).delete()
        
        db_session.flush()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Erreur lors de la fusion des statistiques: {e}")
        db_session.rollback()
        return False

def merge_station_track_stats(db_session: Session, primary_track_id: int, secondary_track_ids: List[int]) -> int:
    """
    Fusionne les statistiques par station des pistes secondaires vers la piste principale.
    
    Args:
        db_session: Session de base de données
        primary_track_id: ID de la piste principale
        secondary_track_ids: Liste des IDs des pistes secondaires
        
    Returns:
        Nombre de statistiques par station migrées
    """
    try:
        # Récupérer toutes les statistiques par station pour les pistes secondaires
        secondary_stats = db_session.query(StationTrackStats).filter(
            StationTrackStats.track_id.in_(secondary_track_ids)
        ).all()
        
        migrated_count = 0
        
        for stats in secondary_stats:
            # Vérifier si des statistiques existent déjà pour cette station et la piste principale
            primary_stats = db_session.query(StationTrackStats).filter(
                StationTrackStats.station_id == stats.station_id,
                StationTrackStats.track_id == primary_track_id
            ).first()
            
            if primary_stats:
                # Mettre à jour les statistiques existantes
                primary_stats.play_count += stats.play_count
                
                if stats.total_play_time:
                    if primary_stats.total_play_time:
                        primary_stats.total_play_time += stats.total_play_time
                    else:
                        primary_stats.total_play_time = stats.total_play_time
                
                if stats.last_played and (not primary_stats.last_played or stats.last_played > primary_stats.last_played):
                    primary_stats.last_played = stats.last_played
                
                if primary_stats.play_count > 0:
                    primary_stats.average_confidence = (
                        (primary_stats.average_confidence * (primary_stats.play_count - stats.play_count) +
                         stats.average_confidence * stats.play_count) /
                        primary_stats.play_count
                    )
            else:
                # Créer de nouvelles statistiques pour la piste principale
                new_stats = StationTrackStats(
                    station_id=stats.station_id,
                    track_id=primary_track_id,
                    play_count=stats.play_count,
                    total_play_time=stats.total_play_time,
                    last_played=stats.last_played,
                    average_confidence=stats.average_confidence
                )
                db_session.add(new_stats)
            
            migrated_count += 1
        
        # Supprimer les statistiques des pistes secondaires
        db_session.query(StationTrackStats).filter(
            StationTrackStats.track_id.in_(secondary_track_ids)
        ).delete()
        
        db_session.flush()
        return migrated_count
    except SQLAlchemyError as e:
        logger.error(f"Erreur lors de la fusion des statistiques par station: {e}")
        db_session.rollback()
        return 0

def merge_fingerprints(db_session: Session, primary_track_id: int, secondary_track_ids: List[int]) -> int:
    """
    Fusionne les empreintes digitales des pistes secondaires vers la piste principale.
    
    Args:
        db_session: Session de base de données
        primary_track_id: ID de la piste principale
        secondary_track_ids: Liste des IDs des pistes secondaires
        
    Returns:
        Nombre d'empreintes migrées
    """
    try:
        # Récupérer toutes les empreintes des pistes secondaires
        secondary_fingerprints = db_session.query(Fingerprint).filter(
            Fingerprint.track_id.in_(secondary_track_ids)
        ).all()
        
        # Récupérer les hashes des empreintes de la piste principale pour éviter les doublons
        primary_hashes = {fp.hash for fp in db_session.query(Fingerprint.hash).filter(
            Fingerprint.track_id == primary_track_id
        ).all()}
        
        migrated_count = 0
        
        for fp in secondary_fingerprints:
            if fp.hash not in primary_hashes:
                # Créer une nouvelle empreinte pour la piste principale
                new_fp = Fingerprint(
                    track_id=primary_track_id,
                    hash=fp.hash,
                    raw_data=fp.raw_data,
                    offset=fp.offset,
                    algorithm=fp.algorithm,
                    created_at=fp.created_at
                )
                db_session.add(new_fp)
                primary_hashes.add(fp.hash)
                migrated_count += 1
        
        # Supprimer les empreintes des pistes secondaires
        db_session.query(Fingerprint).filter(
            Fingerprint.track_id.in_(secondary_track_ids)
        ).delete()
        
        db_session.flush()
        return migrated_count
    except SQLAlchemyError as e:
        logger.error(f"Erreur lors de la fusion des empreintes: {e}")
        db_session.rollback()
        return 0

def delete_secondary_tracks(db_session: Session, secondary_track_ids: List[int]) -> int:
    """
    Supprime les pistes secondaires.
    
    Args:
        db_session: Session de base de données
        secondary_track_ids: Liste des IDs des pistes secondaires
        
    Returns:
        Nombre de pistes supprimées
    """
    try:
        # Supprimer les pistes secondaires
        result = db_session.query(Track).filter(Track.id.in_(secondary_track_ids)).delete()
        db_session.flush()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Erreur lors de la suppression des pistes secondaires: {e}")
        db_session.rollback()
        return 0

def process_duplicate_tracks(db_session: Session, dry_run: bool = False) -> Dict[str, int]:
    """
    Traite les pistes dupliquées.
    
    Args:
        db_session: Session de base de données
        dry_run: Si True, n'effectue pas de modifications dans la base de données
        
    Returns:
        Dictionnaire contenant les statistiques de traitement
    """
    stats = {
        "duplicate_isrc": 0,
        "duplicate_tracks": 0,
        "merged_tracks": 0,
        "merged_detections": 0,
        "merged_stats": 0,
        "merged_station_stats": 0,
        "merged_fingerprints": 0,
        "deleted_tracks": 0,
        "errors": 0
    }
    
    # Trouver les pistes dupliquées
    duplicate_isrc = find_duplicate_isrc(db_session)
    stats["duplicate_isrc"] = len(duplicate_isrc)
    
    for isrc, tracks in duplicate_isrc.items():
        stats["duplicate_tracks"] += len(tracks)
        
        if len(tracks) <= 1:
            continue
        
        logger.info(f"Traitement des pistes avec ISRC {isrc} ({len(tracks)} pistes)")
        
        try:
            # Sélectionner la piste principale
            primary_track = select_primary_track(tracks)
            
            # Identifier les pistes secondaires
            secondary_tracks = [t for t in tracks if t.id != primary_track.id]
            secondary_track_ids = [t.id for t in secondary_tracks]
            
            logger.info(f"Piste principale: ID={primary_track.id}, Titre={primary_track.title}")
            logger.info(f"Pistes secondaires: {secondary_track_ids}")
            
            if not dry_run:
                # Fusionner les détections
                merged_detections = merge_track_detections(db_session, primary_track.id, secondary_track_ids)
                stats["merged_detections"] += merged_detections
                logger.info(f"Détections fusionnées: {merged_detections}")
                
                # Fusionner les statistiques
                if merge_track_stats(db_session, primary_track.id, secondary_track_ids):
                    stats["merged_stats"] += 1
                    logger.info("Statistiques fusionnées avec succès")
                
                # Fusionner les statistiques par station
                merged_station_stats = merge_station_track_stats(db_session, primary_track.id, secondary_track_ids)
                stats["merged_station_stats"] += merged_station_stats
                logger.info(f"Statistiques par station fusionnées: {merged_station_stats}")
                
                # Fusionner les empreintes
                merged_fingerprints = merge_fingerprints(db_session, primary_track.id, secondary_track_ids)
                stats["merged_fingerprints"] += merged_fingerprints
                logger.info(f"Empreintes fusionnées: {merged_fingerprints}")
                
                # Supprimer les pistes secondaires
                deleted_tracks = delete_secondary_tracks(db_session, secondary_track_ids)
                stats["deleted_tracks"] += deleted_tracks
                logger.info(f"Pistes supprimées: {deleted_tracks}")
                
                stats["merged_tracks"] += 1
            else:
                logger.info("Mode dry-run: aucune modification n'a été effectuée")
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement des pistes avec ISRC {isrc}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            stats["errors"] += 1
            db_session.rollback()
    
    if not dry_run:
        db_session.commit()
    
    return stats

def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(description="Recherche et fusionne les pistes dupliquées basées sur l'ISRC.")
    parser.add_argument("--dry-run", action="store_true", help="Exécute le script sans modifier la base de données")
    args = parser.parse_args()
    
    logger.info(f"Démarrage du script de fusion des pistes dupliquées (dry-run: {args.dry_run})")
    
    # Obtenir une session de base de données
    db = next(get_db())
    
    try:
        # Traiter les pistes dupliquées
        stats = process_duplicate_tracks(db, args.dry_run)
        
        # Afficher les statistiques
        logger.info("Statistiques de traitement:")
        logger.info(f"  ISRC dupliqués: {stats['duplicate_isrc']}")
        logger.info(f"  Pistes dupliquées: {stats['duplicate_tracks']}")
        logger.info(f"  Pistes fusionnées: {stats['merged_tracks']}")
        logger.info(f"  Détections fusionnées: {stats['merged_detections']}")
        logger.info(f"  Statistiques fusionnées: {stats['merged_stats']}")
        logger.info(f"  Statistiques par station fusionnées: {stats['merged_station_stats']}")
        logger.info(f"  Empreintes fusionnées: {stats['merged_fingerprints']}")
        logger.info(f"  Pistes supprimées: {stats['deleted_tracks']}")
        logger.info(f"  Erreurs: {stats['errors']}")
        
        if args.dry_run:
            logger.info("Mode dry-run: aucune modification n'a été effectuée dans la base de données")
        else:
            logger.info("Les modifications ont été appliquées à la base de données")
    
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du script: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    logger.info("Script terminé avec succès")

if __name__ == "__main__":
    main() 