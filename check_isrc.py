#!/usr/bin/env python
"""
Script pour vérifier les codes ISRC dans la base de données.
"""

import os
import sys
from pathlib import Path
from sqlalchemy import text

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(str(current_dir.parent))

try:
    # Importer les modules nécessaires
    from models.database import SessionLocal, engine
    from sqlalchemy.exc import SQLAlchemyError

    # Créer une session de base de données
    session = SessionLocal()

    # Vérifier si la table tracks existe
    try:
        result = session.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'tracks')"))
        table_exists = result.scalar()
        print(f"La table 'tracks' existe: {table_exists}")
    except Exception as e:
        print(f"Erreur lors de la vérification de l'existence de la table: {e}")
        table_exists = False

    if table_exists:
        # Vérifier les colonnes de la table tracks
        try:
            result = session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'tracks'"))
            columns = [row[0] for row in result]
            print(f"Colonnes de la table 'tracks': {', '.join(columns)}")
            
            # Vérifier si la colonne isrc existe
            isrc_exists = 'isrc' in columns
            print(f"La colonne 'isrc' existe: {isrc_exists}")
            
            if isrc_exists:
                # Utiliser une requête SQL brute pour éviter les problèmes de modèle
                result = session.execute(text("SELECT id, title, isrc FROM tracks WHERE isrc IS NOT NULL"))
                tracks_with_isrc = result.fetchall()
                
                print(f"Nombre de pistes avec ISRC: {len(tracks_with_isrc)}")
                
                # Afficher les détails des pistes avec ISRC
                if tracks_with_isrc:
                    print("\nDétails des pistes avec ISRC:")
                    for track in tracks_with_isrc:
                        print(f"ID: {track[0]}, Titre: {track[1]}, ISRC: {track[2]}")
                        
                        # Vérifier les détections associées à cette piste
                        try:
                            result = session.execute(text(f"SELECT id, station_id, detection_method, confidence FROM track_detections WHERE track_id = {track[0]}"))
                            detections = result.fetchall()
                            
                            if detections:
                                print(f"  Nombre de détections: {len(detections)}")
                                for detection in detections[:3]:  # Limiter à 3 détections pour éviter trop de sortie
                                    print(f"  - Détection ID: {detection[0]}, Station: {detection[1]}, Méthode: {detection[2]}, Confiance: {detection[3]}")
                            else:
                                print("  Aucune détection associée à cette piste")
                            print()
                        except Exception as e:
                            print(f"  Erreur lors de la récupération des détections: {e}")
                else:
                    print("Aucune piste avec ISRC trouvée dans la base de données.")
                
                # Vérifier les détections qui ont utilisé l'ISRC comme méthode
                try:
                    result = session.execute(text("SELECT id, track_id, station_id, confidence, detected_at, play_duration FROM track_detections WHERE detection_method = 'isrc_match'"))
                    isrc_detections = result.fetchall()
                    
                    print(f"\nNombre de détections utilisant la méthode ISRC: {len(isrc_detections)}")
                    
                    if isrc_detections:
                        print("\nDétails des détections par ISRC:")
                        for detection in isrc_detections[:5]:  # Limiter à 5 détections
                            try:
                                track_result = session.execute(text(f"SELECT title, isrc FROM tracks WHERE id = {detection[1]}"))
                                track = track_result.fetchone()
                                track_title = track[0] if track else "Piste inconnue"
                                track_isrc = track[1] if track else "ISRC inconnu"
                                
                                print(f"Détection ID: {detection[0]}, Piste: {track_title}, ISRC: {track_isrc}")
                                print(f"  Station: {detection[2]}, Confiance: {detection[3]}")
                                print(f"  Détecté à: {detection[4]}, Durée de lecture: {detection[5]}")
                                print()
                            except Exception as e:
                                print(f"  Erreur lors de la récupération des informations de piste: {e}")
                except Exception as e:
                    print(f"Erreur lors de la récupération des détections par ISRC: {e}")
            else:
                print("La colonne 'isrc' n'existe pas dans la table 'tracks'.")
        except Exception as e:
            print(f"Erreur lors de la récupération des colonnes: {e}")
    else:
        print("La table 'tracks' n'existe pas dans la base de données.")

except SQLAlchemyError as e:
    print(f"Erreur de base de données: {e}")
except ImportError as e:
    print(f"Erreur d'importation: {e}")
except Exception as e:
    print(f"Erreur inattendue: {e}") 