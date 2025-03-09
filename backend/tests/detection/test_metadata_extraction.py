#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test unitaire pour vérifier l'extraction et la sauvegarde des métadonnées.

Ce test vérifie que les métadonnées comme l'ISRC, le label, la date de sortie, etc.
sont correctement extraites des résultats de détection et sauvegardées dans la base de données.
"""

import os
import sys
import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track, Artist, TrackDetection, Fingerprint
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.feature_extractor import FeatureExtractor
from backend.utils.logging_config import setup_logging

# Configurer le logging
logger = setup_logging(__name__)

@pytest.fixture
def db_session():
    """Fixture pour créer une session de base de données pour les tests."""
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def track_manager(db_session):
    """Fixture pour créer un TrackManager pour les tests."""
    feature_extractor = FeatureExtractor()
    return TrackManager(db_session, feature_extractor)

@pytest.fixture
def sample_metadata():
    """Fixture pour créer des métadonnées d'exemple."""
    return {
        "title": "Test Track",
        "artist": "Test Artist",
        "album": "Test Album",
        "isrc": "USRC12345678",
        "label": "Test Label",
        "release_date": "2023-01-01",
        "fingerprint": "test_fingerprint_hash",
        "fingerprint_raw": b"test_fingerprint_raw_data",
        "chromaprint": "test_chromaprint_data",
        "features": {
            "mfcc_mean": [0.1, 0.2, 0.3],
            "chroma_mean": [0.4, 0.5, 0.6],
            "spectral_centroid_mean": 0.7
        }
    }

@pytest.mark.asyncio
async def test_metadata_extraction_and_saving(db_session, track_manager, sample_metadata):
    """
    Teste l'extraction et la sauvegarde des métadonnées.
    
    Ce test vérifie que :
    1. Les métadonnées sont correctement extraites des résultats de détection
    2. Les métadonnées sont correctement sauvegardées dans la base de données
    3. Les métadonnées peuvent être récupérées de la base de données
    """
    # 1. Créer une piste avec les métadonnées d'exemple
    track = await track_manager._get_or_create_track(
        title=sample_metadata["title"],
        artist_name=sample_metadata["artist"],
        features=sample_metadata
    )
    
    # Vérifier que la piste a été créée
    assert track is not None, "La piste n'a pas été créée"
    assert track.title == sample_metadata["title"], f"Titre incorrect: {track.title} != {sample_metadata['title']}"
    assert track.artist.name == sample_metadata["artist"], f"Artiste incorrect: {track.artist.name} != {sample_metadata['artist']}"
    
    # 2. Vérifier que les métadonnées ont été sauvegardées
    assert track.isrc == sample_metadata["isrc"], f"ISRC incorrect: {track.isrc} != {sample_metadata['isrc']}"
    assert track.label == sample_metadata["label"], f"Label incorrect: {track.label} != {sample_metadata['label']}"
    assert track.album == sample_metadata["album"], f"Album incorrect: {track.album} != {sample_metadata['album']}"
    assert track.release_date == sample_metadata["release_date"], f"Date de sortie incorrecte: {track.release_date} != {sample_metadata['release_date']}"
    
    # 3. Vérifier que l'empreinte a été sauvegardée
    assert track.fingerprint == sample_metadata["fingerprint"], f"Empreinte incorrecte: {track.fingerprint} != {sample_metadata['fingerprint']}"
    assert track.chromaprint == sample_metadata["chromaprint"], f"Chromaprint incorrect: {track.chromaprint} != {sample_metadata['chromaprint']}"
    
    # 4. Vérifier que l'empreinte a été sauvegardée dans la table fingerprints
    fingerprints = db_session.query(Fingerprint).filter_by(track_id=track.id).all()
    assert len(fingerprints) > 0, "Aucune empreinte trouvée dans la table fingerprints"
    
    # Vérifier qu'il y a au moins une empreinte de type "chromaprint"
    chromaprint_fingerprints = [fp for fp in fingerprints if fp.algorithm == "chromaprint"]
    assert len(chromaprint_fingerprints) > 0, "Aucune empreinte Chromaprint trouvée dans la table fingerprints"
    
    # 5. Simuler une détection complète
    station_id = 1
    
    # Démarrer la détection
    detection_result = track_manager._start_track_detection(track, station_id, sample_metadata)
    assert detection_result is not None, "Échec du démarrage de la détection"
    
    # Finaliser la détection
    track_manager._end_current_track(station_id)
    
    # 6. Vérifier que la détection a été enregistrée
    detections = db_session.query(TrackDetection).filter_by(track_id=track.id, station_id=station_id).all()
    assert len(detections) > 0, "Aucune détection enregistrée"
    
    # Vérifier que la dernière détection a une durée de lecture
    latest_detection = max(detections, key=lambda d: d.detected_at)
    assert latest_detection.play_duration is not None, "La durée de lecture n'a pas été enregistrée"
    
    # 7. Nettoyer la base de données
    # Supprimer les détections
    for detection in detections:
        db_session.delete(detection)
    
    # Supprimer les empreintes
    for fingerprint in fingerprints:
        db_session.delete(fingerprint)
    
    # Supprimer la piste
    db_session.delete(track)
    
    # Supprimer l'artiste si nécessaire
    artist = db_session.query(Artist).filter_by(name=sample_metadata["artist"]).first()
    if artist and len(artist.tracks) == 0:
        db_session.delete(artist)
    
    db_session.commit()

@pytest.mark.asyncio
async def test_isrc_extraction_from_external_services(db_session, track_manager):
    """
    Teste l'extraction de l'ISRC à partir des résultats des services externes.
    
    Ce test vérifie que :
    1. L'ISRC est correctement extrait des résultats d'AudD
    2. L'ISRC est correctement extrait des résultats d'AcoustID
    3. L'ISRC est correctement sauvegardé dans la base de données
    """
    # 1. Simuler un résultat d'AudD avec un ISRC
    audd_result = {
        "title": "AudD Track",
        "artist": "AudD Artist",
        "album": "AudD Album",
        "label": "AudD Label",
        "release_date": "2023-02-02",
        "apple_music": {
            "isrc": "USRC23456789"
        }
    }
    
    # Créer une piste avec les résultats d'AudD
    audd_track = await track_manager._get_or_create_track(
        title=audd_result["title"],
        artist_name=audd_result["artist"],
        features=audd_result
    )
    
    # Vérifier que l'ISRC a été extrait et sauvegardé
    assert audd_track.isrc == "USRC23456789", f"ISRC incorrect: {audd_track.isrc} != USRC23456789"
    
    # 2. Simuler un résultat d'AcoustID avec un ISRC
    acoustid_result = {
        "title": "AcoustID Track",
        "artist": "AcoustID Artist",
        "album": "AcoustID Album",
        "isrc": "USRC34567890",
        "label": "AcoustID Label",
        "release_date": "2023-03-03"
    }
    
    # Créer une piste avec les résultats d'AcoustID
    acoustid_track = await track_manager._get_or_create_track(
        title=acoustid_result["title"],
        artist_name=acoustid_result["artist"],
        features=acoustid_result
    )
    
    # Vérifier que l'ISRC a été extrait et sauvegardé
    assert acoustid_track.isrc == "USRC34567890", f"ISRC incorrect: {acoustid_track.isrc} != USRC34567890"
    
    # 3. Simuler un résultat d'AudD avec un ISRC dans Spotify
    spotify_result = {
        "title": "Spotify Track",
        "artist": "Spotify Artist",
        "album": "Spotify Album",
        "label": "Spotify Label",
        "release_date": "2023-04-04",
        "spotify": {
            "external_ids": {
                "isrc": "USRC45678901"
            }
        }
    }
    
    # Créer une piste avec les résultats de Spotify
    spotify_track = await track_manager._get_or_create_track(
        title=spotify_result["title"],
        artist_name=spotify_result["artist"],
        features=spotify_result
    )
    
    # Vérifier que l'ISRC a été extrait et sauvegardé
    assert spotify_track.isrc == "USRC45678901", f"ISRC incorrect: {spotify_track.isrc} != USRC45678901"
    
    # 4. Simuler un résultat d'AudD avec un ISRC dans Deezer
    deezer_result = {
        "title": "Deezer Track",
        "artist": "Deezer Artist",
        "album": "Deezer Album",
        "label": "Deezer Label",
        "release_date": "2023-05-05",
        "deezer": {
            "isrc": "USRC56789012"
        }
    }
    
    # Créer une piste avec les résultats de Deezer
    deezer_track = await track_manager._get_or_create_track(
        title=deezer_result["title"],
        artist_name=deezer_result["artist"],
        features=deezer_result
    )
    
    # Vérifier que l'ISRC a été extrait et sauvegardé
    assert deezer_track.isrc == "USRC56789012", f"ISRC incorrect: {deezer_track.isrc} != USRC56789012"
    
    # 5. Nettoyer la base de données
    for track in [audd_track, acoustid_track, spotify_track, deezer_track]:
        # Supprimer les empreintes
        fingerprints = db_session.query(Fingerprint).filter_by(track_id=track.id).all()
        for fingerprint in fingerprints:
            db_session.delete(fingerprint)
        
        # Supprimer la piste
        db_session.delete(track)
    
    # Supprimer les artistes
    for artist_name in ["AudD Artist", "AcoustID Artist", "Spotify Artist", "Deezer Artist"]:
        artist = db_session.query(Artist).filter_by(name=artist_name).first()
        if artist and len(artist.tracks) == 0:
            db_session.delete(artist)
    
    db_session.commit()

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 