#!/usr/bin/env python
"""
Script pour vérifier les codes ISRC dans la base de données.
"""

import os
import sys
from pathlib import Path

try:
    # Importer les modules nécessaires
    from models.database import SessionLocal
    from models.models import Track, TrackDetection
    from sqlalchemy.exc import SQLAlchemyError

    # Créer une session de base de données
    session = SessionLocal()

    # Vérifier les pistes avec des codes ISRC
    tracks_with_isrc = session.query(Track).filter(Track.isrc != None).all()
    
    print(f"Nombre de pistes avec ISRC: {len(tracks_with_isrc)}")
    
    # Afficher les détails des pistes avec ISRC
    if tracks_with_isrc:
        print("\nDétails des pistes avec ISRC:")
        for track in tracks_with_isrc:
            print(f"ID: {track.id}, Titre: {track.title}, ISRC: {track.isrc}")
            
            # Vérifier les détections associées à cette piste
            detections = session.query(TrackDetection).filter(TrackDetection.track_id == track.id).all()
            if detections:
                print(f"  Nombre de détections: {len(detections)}")
                for detection in detections[:3]:  # Limiter à 3 détections pour éviter trop de sortie
                    print(f"  - Détection ID: {detection.id}, Station: {detection.station_id}, Méthode: {detection.detection_method}, Confiance: {detection.confidence}")
            else:
                print("  Aucune détection associée à cette piste")
            print()
    else:
        print("Aucune piste avec ISRC trouvée dans la base de données.")
    
    # Vérifier les détections qui ont utilisé l'ISRC comme méthode
    isrc_detections = session.query(TrackDetection).filter(TrackDetection.detection_method == 'isrc_match').all()
    
    print(f"\nNombre de détections utilisant la méthode ISRC: {len(isrc_detections)}")
    
    if isrc_detections:
        print("\nDétails des détections par ISRC:")
        for detection in isrc_detections[:5]:  # Limiter à 5 détections
            track = session.query(Track).filter(Track.id == detection.track_id).first()
            track_title = track.title if track else "Piste inconnue"
            track_isrc = track.isrc if track else "ISRC inconnu"
            
            print(f"Détection ID: {detection.id}, Piste: {track_title}, ISRC: {track_isrc}")
            print(f"  Station: {detection.station_id}, Confiance: {detection.confidence}")
            print(f"  Détecté à: {detection.detected_at}, Durée de lecture: {detection.play_duration}")
            print()

except SQLAlchemyError as e:
    print(f"Erreur de base de données: {e}")
except ImportError as e:
    print(f"Erreur d'importation: {e}")
except Exception as e:
    print(f"Erreur inattendue: {e}") 