#!/usr/bin/env python
"""
Script pour vérifier directement les codes ISRC dans la base de données PostgreSQL.
"""

import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Récupérer l'URL de la base de données
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("La variable d'environnement DATABASE_URL n'est pas définie.")
    database_url = os.getenv("DEV_DATABASE_URL", "postgresql://postgres:postgres@db:5432/sodav_dev")
    print(f"Utilisation de l'URL par défaut: {database_url}")

try:
    # Extraire les informations de connexion de l'URL
    if database_url.startswith("postgresql://"):
        # Format: postgresql://user:password@host:port/dbname
        parts = database_url.replace("postgresql://", "").split("/")
        dbname = parts[1]
        auth_host_port = parts[0].split("@")
        host_port = auth_host_port[1].split(":")
        auth = auth_host_port[0].split(":")
        
        user = auth[0]
        password = auth[1] if len(auth) > 1 else ""
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else "5432"
        
        print(f"Connexion à la base de données: {host}:{port}/{dbname} en tant que {user}")
        
        # Se connecter à la base de données
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
    else:
        print(f"Format d'URL non pris en charge: {database_url}")
        exit(1)
    
    # Créer un curseur
    cur = conn.cursor()
    
    # Vérifier si la table tracks existe
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'tracks')")
    table_exists = cur.fetchone()[0]
    print(f"La table 'tracks' existe: {table_exists}")
    
    if table_exists:
        # Vérifier les colonnes de la table tracks
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'tracks'")
        columns = [row[0] for row in cur.fetchall()]
        print(f"Colonnes de la table 'tracks': {', '.join(columns)}")
        
        # Vérifier si la colonne isrc existe
        isrc_exists = 'isrc' in columns
        print(f"La colonne 'isrc' existe: {isrc_exists}")
        
        if isrc_exists:
            # Récupérer les pistes avec des codes ISRC
            cur.execute("SELECT id, title, isrc FROM tracks WHERE isrc IS NOT NULL")
            tracks_with_isrc = cur.fetchall()
            
            print(f"Nombre de pistes avec ISRC: {len(tracks_with_isrc)}")
            
            # Afficher les détails des pistes avec ISRC
            if tracks_with_isrc:
                print("\nDétails des pistes avec ISRC:")
                for track in tracks_with_isrc:
                    print(f"ID: {track[0]}, Titre: {track[1]}, ISRC: {track[2]}")
                    
                    # Vérifier les détections associées à cette piste
                    cur.execute("SELECT id, station_id, detection_method, confidence FROM track_detections WHERE track_id = %s", (track[0],))
                    detections = cur.fetchall()
                    
                    if detections:
                        print(f"  Nombre de détections: {len(detections)}")
                        for detection in detections[:3]:  # Limiter à 3 détections pour éviter trop de sortie
                            print(f"  - Détection ID: {detection[0]}, Station: {detection[1]}, Méthode: {detection[2]}, Confiance: {detection[3]}")
                    else:
                        print("  Aucune détection associée à cette piste")
                    print()
            else:
                print("Aucune piste avec ISRC trouvée dans la base de données.")
            
            # Vérifier les détections qui ont utilisé l'ISRC comme méthode
            cur.execute("SELECT id, track_id, station_id, confidence, detected_at, play_duration FROM track_detections WHERE detection_method = 'isrc_match'")
            isrc_detections = cur.fetchall()
            
            print(f"\nNombre de détections utilisant la méthode ISRC: {len(isrc_detections)}")
            
            if isrc_detections:
                print("\nDétails des détections par ISRC:")
                for detection in isrc_detections[:5]:  # Limiter à 5 détections
                    cur.execute("SELECT title, isrc FROM tracks WHERE id = %s", (detection[1],))
                    track = cur.fetchone()
                    track_title = track[0] if track else "Piste inconnue"
                    track_isrc = track[1] if track else "ISRC inconnu"
                    
                    print(f"Détection ID: {detection[0]}, Piste: {track_title}, ISRC: {track_isrc}")
                    print(f"  Station: {detection[2]}, Confiance: {detection[3]}")
                    print(f"  Détecté à: {detection[4]}, Durée de lecture: {detection[5]}")
                    print()
        else:
            print("La colonne 'isrc' n'existe pas dans la table 'tracks'.")
    else:
        print("La table 'tracks' n'existe pas dans la base de données.")
    
    # Fermer le curseur et la connexion
    cur.close()
    conn.close()

except psycopg2.Error as e:
    print(f"Erreur PostgreSQL: {e}")
except Exception as e:
    print(f"Erreur inattendue: {e}") 