#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier et mettre à jour les empreintes digitales des pistes existantes.
Usage: python update_track_fingerprints.py [--track_id TRACK_ID]
"""

import os
import sys
import json
import hashlib
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_fingerprints(track_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Vérifie les empreintes digitales des pistes et identifie celles qui sont invalides ou manquantes.
    
    Args:
        track_id: ID de la piste à vérifier (si None, vérifie toutes les pistes)
        
    Returns:
        Liste des pistes avec des problèmes d'empreintes digitales
    """
    # Initialiser la base de données
    init_db()
    
    # Créer une session de base de données
    db_session = SessionLocal()
    
    try:
        # Préparer la requête
        query = db_session.query(Track)
        if track_id:
            query = query.filter(Track.id == track_id)
        
        # Récupérer les pistes
        tracks = query.all()
        logger.info(f"Vérification de {len(tracks)} piste(s)")
        
        # Liste des pistes avec des problèmes
        problematic_tracks = []
        
        for track in tracks:
            problems = []
            
            # Vérifier si fingerprint est manquant
            if not track.fingerprint:
                problems.append("Fingerprint hash manquant")
            
            # Vérifier si fingerprint_raw est manquant
            if not track.fingerprint_raw:
                problems.append("Fingerprint raw manquant")
            
            # Vérifier si fingerprint et fingerprint_raw sont cohérents
            elif track.fingerprint:
                # Calculer le hash à partir de fingerprint_raw
                calculated_hash = hashlib.md5(track.fingerprint_raw).hexdigest()
                
                # Comparer avec le hash stocké
                if calculated_hash != track.fingerprint:
                    problems.append(f"Incohérence entre fingerprint hash et raw (hash stocké: {track.fingerprint[:10]}..., hash calculé: {calculated_hash[:10]}...)")
            
            # Si des problèmes ont été identifiés, ajouter la piste à la liste
            if problems:
                problematic_tracks.append({
                    "id": track.id,
                    "title": track.title,
                    "artist_id": track.artist_id,
                    "problems": problems
                })
        
        return problematic_tracks
    
    finally:
        # Fermer la session de base de données
        db_session.close()

def update_fingerprints(problematic_tracks: List[Dict[str, Any]]) -> int:
    """
    Met à jour les empreintes digitales des pistes problématiques.
    
    Args:
        problematic_tracks: Liste des pistes avec des problèmes d'empreintes digitales
        
    Returns:
        Nombre de pistes mises à jour
    """
    if not problematic_tracks:
        logger.info("Aucune piste à mettre à jour")
        return 0
    
    # Initialiser la base de données
    init_db()
    
    # Créer une session de base de données
    db_session = SessionLocal()
    
    try:
        updated_count = 0
        
        for track_info in problematic_tracks:
            track_id = track_info["id"]
            track = db_session.query(Track).filter(Track.id == track_id).first()
            
            if not track:
                logger.warning(f"Piste avec ID {track_id} non trouvée")
                continue
            
            # Générer de nouvelles empreintes si nécessaire
            if "Fingerprint raw manquant" in track_info["problems"] or "Incohérence entre fingerprint hash et raw" in track_info["problems"][0]:
                # Créer des données de base pour l'empreinte
                fingerprint_data = {
                    "id": track.id,
                    "title": track.title,
                    "artist_id": track.artist_id,
                    "timestamp": str(track.created_at)
                }
                
                # Convertir en chaîne JSON pour les données brutes
                fingerprint_raw_str = json.dumps(fingerprint_data, sort_keys=True)
                fingerprint_raw = fingerprint_raw_str.encode('utf-8')
                
                # Calculer le hash MD5 pour l'empreinte de recherche
                fingerprint_hash = hashlib.md5(fingerprint_raw).hexdigest()
                
                # Mettre à jour la piste
                track.fingerprint = fingerprint_hash
                track.fingerprint_raw = fingerprint_raw
                
                logger.info(f"Mise à jour des empreintes pour la piste {track.id} ({track.title})")
                updated_count += 1
            
            # Si seulement le hash est manquant mais raw est présent
            elif "Fingerprint hash manquant" in track_info["problems"] and track.fingerprint_raw:
                # Calculer le hash à partir de fingerprint_raw
                fingerprint_hash = hashlib.md5(track.fingerprint_raw).hexdigest()
                
                # Mettre à jour la piste
                track.fingerprint = fingerprint_hash
                
                logger.info(f"Mise à jour du hash d'empreinte pour la piste {track.id} ({track.title})")
                updated_count += 1
        
        # Commit des changements
        db_session.commit()
        
        return updated_count
    
    finally:
        # Fermer la session de base de données
        db_session.close()

def main():
    """
    Fonction principale.
    """
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Vérifier et mettre à jour les empreintes digitales des pistes")
    parser.add_argument("--track_id", type=int, help="ID de la piste à vérifier (si non spécifié, vérifie toutes les pistes)")
    parser.add_argument("--update", action="store_true", help="Mettre à jour les empreintes digitales problématiques")
    args = parser.parse_args()
    
    # Vérifier les empreintes digitales
    problematic_tracks = validate_fingerprints(args.track_id)
    
    # Afficher les résultats
    if problematic_tracks:
        logger.info(f"Trouvé {len(problematic_tracks)} piste(s) avec des problèmes d'empreintes digitales:")
        for track in problematic_tracks:
            logger.info(f"  Piste {track['id']} ({track['title']}): {', '.join(track['problems'])}")
        
        # Mettre à jour les empreintes si demandé
        if args.update:
            updated_count = update_fingerprints(problematic_tracks)
            logger.info(f"Mis à jour {updated_count} piste(s)")
    else:
        logger.info("Aucun problème d'empreinte digitale trouvé")

if __name__ == "__main__":
    main() 