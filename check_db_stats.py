#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier les statistiques de la base de données PostgreSQL
"""

import psycopg2
import sys

def check_db_stats():
    """Vérifie les statistiques de la base de données"""
    try:
        # Connexion à la base de données
        conn = psycopg2.connect('postgresql://postgres:postgres@localhost/sodav_dev')
        cursor = conn.cursor()
        
        # Vérifier le nombre de pistes
        cursor.execute('SELECT COUNT(*) FROM tracks')
        print('Nombre de pistes:', cursor.fetchone()[0])
        
        # Vérifier le nombre de détections
        cursor.execute('SELECT COUNT(*) FROM track_detections')
        print('Nombre de détections:', cursor.fetchone()[0])
        
        # Vérifier le nombre de pistes avec ISRC
        cursor.execute('SELECT COUNT(*) FROM tracks WHERE isrc IS NOT NULL')
        print('Pistes avec ISRC:', cursor.fetchone()[0])
        
        # Vérifier le nombre de pistes avec label
        cursor.execute('SELECT COUNT(*) FROM tracks WHERE label IS NOT NULL')
        print('Pistes avec label:', cursor.fetchone()[0])
        
        # Vérifier si la table fingerprints existe
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'fingerprints'")
        fingerprints_exists = cursor.fetchone() is not None
        
        if fingerprints_exists:
            cursor.execute('SELECT COUNT(*) FROM fingerprints')
            print('Nombre d\'empreintes:', cursor.fetchone()[0])
        else:
            print('Table fingerprints n\'existe pas')
        
        # Afficher quelques pistes avec leurs métadonnées
        print("\nExemples de pistes avec métadonnées:")
        cursor.execute('''
            SELECT t.id, t.title, a.name as artist, t.isrc, t.label, t.album, t.release_date
            FROM tracks t
            JOIN artists a ON t.artist_id = a.id
            WHERE t.isrc IS NOT NULL OR t.label IS NOT NULL
            LIMIT 5
        ''')
        
        rows = cursor.fetchall()
        for row in rows:
            print(f"ID: {row[0]}, Titre: {row[1]}, Artiste: {row[2]}, ISRC: {row[3]}, Label: {row[4]}, Album: {row[5]}, Date: {row[6]}")
        
        # Afficher quelques détections
        print("\nExemples de détections:")
        cursor.execute('''
            SELECT td.id, t.title, a.name as artist, td.detected_at, td.play_duration, td.detection_method, td.confidence
            FROM track_detections td
            JOIN tracks t ON td.track_id = t.id
            JOIN artists a ON t.artist_id = a.id
            ORDER BY td.detected_at DESC
            LIMIT 5
        ''')
        
        rows = cursor.fetchall()
        for row in rows:
            print(f"ID: {row[0]}, Titre: {row[1]}, Artiste: {row[2]}, Détecté: {row[3]}, Durée: {row[4]}, Méthode: {row[5]}, Confiance: {row[6]}")
        
        # Fermer la connexion
        conn.close()
        
    except Exception as e:
        print(f"Erreur: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(check_db_stats()) 