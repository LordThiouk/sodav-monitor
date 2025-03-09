#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test unitaire pour la détection locale avec empreintes multiples.

Ce test vérifie que la méthode find_local_match du TrackManager utilise correctement
la nouvelle table fingerprints pour rechercher des correspondances.
"""

import os
import sys
import asyncio
import pytest
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import hashlib
import uuid

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(parent_dir))

from backend.models.database import init_db, SessionLocal
from backend.models.models import Track, Artist, Fingerprint
from backend.detection.audio_processor.track_manager import TrackManager
from backend.detection.audio_processor.feature_extractor import FeatureExtractor

# Configuration du test
@pytest.fixture
def db_session():
    """Crée une session de base de données pour les tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def track_manager(db_session):
    """Crée un TrackManager pour les tests."""
    feature_extractor = FeatureExtractor()
    return TrackManager(db_session, feature_extractor)

@pytest.fixture
async def test_track_with_multiple_fingerprints(db_session):
    """Crée une piste de test avec plusieurs empreintes digitales."""
    # Créer un artiste de test avec un nom unique
    unique_name = f"Test Artist {uuid.uuid4()}"
    
    # Vérifier si l'artiste existe déjà
    existing_artist = db_session.query(Artist).filter_by(name=unique_name).first()
    if existing_artist:
        artist = existing_artist
    else:
        artist = Artist(name=unique_name)
        db_session.add(artist)
        db_session.flush()
    
    # Créer une piste de test
    track = Track(
        title="Test Track",
        artist_id=artist.id,
        isrc="TESTABC12345",
        label="Test Label",
        album="Test Album"
    )
    db_session.add(track)
    db_session.flush()
    
    # Créer plusieurs empreintes pour la piste
    fingerprints = []
    for i in range(5):
        # Générer une empreinte unique
        data = f"test_fingerprint_{i}_{track.id}"
        fingerprint_hash = hashlib.md5(data.encode()).hexdigest()
        fingerprint_raw = data.encode()
        
        # Créer l'empreinte dans la base de données
        fingerprint = Fingerprint(
            track_id=track.id,
            hash=fingerprint_hash,
            raw_data=fingerprint_raw,
            offset=i * 5.0,  # Position dans la piste (en secondes)
            algorithm="md5"
        )
        db_session.add(fingerprint)
        fingerprints.append(fingerprint_hash)
    
    # Ajouter également une empreinte dans la colonne fingerprint de la piste
    track.fingerprint = fingerprints[0]
    track.fingerprint_raw = f"test_fingerprint_0_{track.id}".encode()
    
    db_session.commit()
    
    return {
        "track": track,
        "fingerprints": fingerprints,
        "artist_name": unique_name
    }

@pytest.mark.asyncio
async def test_find_local_match_with_fingerprints_table(track_manager, test_track_with_multiple_fingerprints):
    """
    Teste la méthode find_local_match avec la table fingerprints.
    
    Ce test vérifie que la méthode find_local_match du TrackManager utilise correctement
    la nouvelle table fingerprints pour rechercher des correspondances.
    """
    track_data = test_track_with_multiple_fingerprints
    track = track_data["track"]
    fingerprints = track_data["fingerprints"]
    
    # Tester la détection avec chaque empreinte
    for i, fingerprint_hash in enumerate(fingerprints):
        # Créer des caractéristiques fictives avec l'empreinte
        features = {
            "fingerprint": fingerprint_hash
        }
        
        # Rechercher une correspondance locale
        match = await track_manager.find_local_match(features)
        
        # Vérifier que la piste a été trouvée
        assert match is not None, f"La piste n'a pas été trouvée avec l'empreinte {i}"
        assert match["id"] == track.id, f"L'ID de la piste ne correspond pas pour l'empreinte {i}"
        assert match["title"] == track.title, f"Le titre de la piste ne correspond pas pour l'empreinte {i}"
        assert match["confidence"] == 1.0, f"La confiance n'est pas de 1.0 pour l'empreinte {i}"
        assert match["source"] == "local", f"La source n'est pas 'local' pour l'empreinte {i}"

@pytest.mark.asyncio
async def test_find_local_match_with_similarity(track_manager, test_track_with_multiple_fingerprints, db_session):
    """
    Teste la méthode find_local_match avec une recherche par similarité.
    
    Ce test vérifie que la méthode find_local_match du TrackManager peut trouver
    des correspondances par similarité lorsqu'il n'y a pas de correspondance exacte.
    """
    track_data = test_track_with_multiple_fingerprints
    track = track_data["track"]
    
    # Créer une empreinte similaire mais pas identique
    similar_fingerprint = hashlib.md5(f"similar_to_{track.id}".encode()).hexdigest()
    
    # Créer des caractéristiques fictives avec l'empreinte similaire
    features = {
        "fingerprint": similar_fingerprint
    }
    
    # Modifier temporairement la méthode _calculate_similarity pour retourner un score élevé
    original_calculate_similarity = track_manager._calculate_similarity
    
    def mock_calculate_similarity(features1, features2):
        # Retourner un score élevé pour simuler une similarité
        return 0.8
    
    track_manager._calculate_similarity = mock_calculate_similarity
    
    try:
        # Rechercher une correspondance locale
        match = await track_manager.find_local_match(features)
        
        # Vérifier que la piste a été trouvée par similarité
        assert match is not None, "La piste n'a pas été trouvée par similarité"
        assert "id" in match, "L'ID de la piste n'est pas présent dans le résultat"
        assert "title" in match, "Le titre de la piste n'est pas présent dans le résultat"
        assert "artist" in match, "L'artiste de la piste n'est pas présent dans le résultat"
        assert match["confidence"] < 1.0, "La confiance devrait être inférieure à 1.0 pour une correspondance par similarité"
        assert match["source"] == "local", "La source n'est pas 'local'"
    finally:
        # Restaurer la méthode originale
        track_manager._calculate_similarity = original_calculate_similarity

@pytest.mark.asyncio
async def test_find_local_match_no_match(track_manager):
    """
    Teste la méthode find_local_match lorsqu'aucune correspondance n'est trouvée.
    
    Ce test vérifie que la méthode find_local_match du TrackManager retourne None
    lorsqu'aucune correspondance n'est trouvée.
    """
    # Créer une empreinte qui n'existe pas dans la base de données
    non_existent_fingerprint = hashlib.md5(b"non_existent_fingerprint").hexdigest()
    
    # Créer des caractéristiques fictives avec l'empreinte inexistante
    features = {
        "fingerprint": non_existent_fingerprint
    }
    
    # Rechercher une correspondance locale
    match = await track_manager.find_local_match(features)
    
    # Vérifier qu'aucune piste n'a été trouvée
    assert match is None, "Une piste a été trouvée alors qu'aucune correspondance ne devrait exister"

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 