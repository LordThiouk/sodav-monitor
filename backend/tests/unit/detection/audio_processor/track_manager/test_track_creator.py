"""
Tests unitaires pour la classe TrackCreator.

Ce module contient les tests unitaires pour la classe TrackCreator qui est responsable
de la création et de la mise à jour des pistes et des artistes dans la base de données.
"""

import asyncio
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from backend.detection.audio_processor.track_manager.track_creator import TrackCreator
from backend.models.models import Artist, Track


# Fixtures pour les tests
@pytest.fixture
def db_session():
    """Crée une session de base de données simulée pour les tests."""
    mock_session = MagicMock(spec=Session)
    return mock_session


@pytest.fixture
def track_creator(db_session):
    """Crée une instance de TrackCreator pour les tests."""
    return TrackCreator(db_session)


@pytest.mark.asyncio
async def test_get_or_create_artist_existing(track_creator, db_session):
    """Teste la récupération d'un artiste existant."""
    # Configurer le mock pour simuler un artiste existant
    mock_artist = MagicMock(spec=Artist)
    mock_artist.id = 1
    mock_artist.name = "Test Artist"

    # Configurer la requête pour retourner l'artiste simulé
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_artist
    db_session.query.return_value = mock_query

    # Appeler la méthode à tester
    artist_id = await track_creator.get_or_create_artist("Test Artist")

    # Vérifier les résultats
    assert artist_id == 1

    # Vérifier les appels de méthode
    db_session.query.assert_called_once_with(Artist)
    mock_query.filter.assert_called_once()
    db_session.add.assert_not_called()
    db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_artist_new(track_creator, db_session):
    """Teste la création d'un nouvel artiste."""
    # Configurer le mock pour simuler qu'aucun artiste n'existe
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None
    db_session.query.return_value = mock_query

    # Configurer le mock pour simuler la création d'un nouvel artiste
    def side_effect_add(artist):
        artist.id = 2

    db_session.add.side_effect = side_effect_add

    # Appeler la méthode à tester
    artist_id = await track_creator.get_or_create_artist("New Artist")

    # Vérifier les résultats
    assert artist_id == 2

    # Vérifier les appels de méthode
    db_session.query.assert_called_once_with(Artist)
    mock_query.filter.assert_called_once()
    db_session.add.assert_called_once()
    db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_artist_empty_name(track_creator, db_session):
    """Teste la création d'un artiste avec un nom vide."""
    # Configurer le mock pour simuler qu'aucun artiste n'existe
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None
    db_session.query.return_value = mock_query

    # Configurer le mock pour simuler la création d'un nouvel artiste
    def side_effect_add(artist):
        artist.id = 3
        assert artist.name == "Unknown Artist"

    db_session.add.side_effect = side_effect_add

    # Appeler la méthode à tester avec un nom vide
    artist_id = await track_creator.get_or_create_artist("")

    # Vérifier les résultats
    assert artist_id == 3

    # Vérifier les appels de méthode
    db_session.query.assert_called_once_with(Artist)
    mock_query.filter.assert_called_once()
    db_session.add.assert_called_once()
    db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_track_existing(track_creator, db_session):
    """Teste la récupération d'une piste existante."""
    # Configurer le mock pour simuler une piste existante
    mock_track = MagicMock(spec=Track)
    mock_track.id = 1
    mock_track.title = "Test Track"
    mock_track.artist_id = 1
    mock_track.album = "Test Album"
    mock_track.isrc = "ABCDE1234567"

    # Configurer la requête pour retourner la piste simulée
    mock_query = MagicMock()
    mock_query.filter.return_value.filter.return_value.first.return_value = mock_track
    db_session.query.return_value = mock_query

    # Appeler la méthode à tester
    track = await track_creator.get_or_create_track(
        title="Test Track", artist_id=1, album="Test Album", isrc="ABCDE1234567"
    )

    # Vérifier les résultats
    assert track.id == 1
    assert track.title == "Test Track"
    assert track.artist_id == 1

    # Vérifier les appels de méthode
    db_session.query.assert_called_once_with(Track)
    mock_query.filter.assert_called_once()
    db_session.add.assert_not_called()
    db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_track_new(track_creator, db_session):
    """Teste la création d'une nouvelle piste."""
    # Configurer le mock pour simuler qu'aucune piste n'existe
    mock_query = MagicMock()
    mock_query.filter.return_value.filter.return_value.first.return_value = None
    db_session.query.return_value = mock_query

    # Créer un mock pour la nouvelle piste
    mock_new_track = MagicMock(spec=Track)
    mock_new_track.id = 2
    mock_new_track.title = "New Track"
    mock_new_track.artist_id = 1
    mock_new_track.album = "New Album"
    mock_new_track.isrc = "ABCDE1234567"

    # Patch la création de Track pour retourner notre mock
    with patch("backend.models.models.Track", return_value=mock_new_track):
        # Appeler la méthode à tester
        track = await track_creator.get_or_create_track(
            title="New Track", artist_id=1, album="New Album", isrc="ABCDE1234567", duration=180.5
        )

        # Vérifier les résultats
        assert track.id == 2
        assert track.title == "New Track"
        assert track.artist_id == 1

        # Vérifier les appels de méthode
        db_session.query.assert_called_once_with(Track)
        db_session.add.assert_called_once_with(mock_new_track)
        db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_track_update_existing(track_creator, db_session):
    """Teste la mise à jour d'une piste existante avec de nouvelles informations."""
    # Créer un mock pour la piste existante
    mock_track = MagicMock(spec=Track)
    mock_track.id = 1
    mock_track.title = "Test Track"
    mock_track.artist_id = 1
    mock_track.album = None
    mock_track.isrc = None
    mock_track.label = None
    mock_track.release_date = None

    # Configurer la requête pour retourner la piste simulée
    mock_query = MagicMock()
    mock_query.filter.return_value.filter.return_value.first.return_value = mock_track
    db_session.query.return_value = mock_query

    # Appeler la méthode à tester avec des informations supplémentaires
    result = await track_creator.get_or_create_track(
        title="Test Track",
        artist_id=1,
        album="Updated Album",
        isrc="ABCDE1234567",
        label="Test Label",
        release_date="2023-01-01",
    )

    # Vérifier que la piste a été mise à jour
    assert result is mock_track
    assert mock_track.album == "Updated Album"
    assert mock_track.isrc == "ABCDE1234567"
    assert mock_track.label == "Test Label"
    assert mock_track.release_date == "2023-01-01"

    # Vérifier les appels de méthode
    db_session.query.assert_called_once_with(Track)
    db_session.add.assert_not_called()  # Pas besoin d'ajouter une piste existante
    db_session.commit.assert_called_once()  # Commit pour sauvegarder les modifications


@pytest.mark.asyncio
async def test_get_or_create_track_invalid_title(track_creator, db_session):
    """Teste la création d'une piste avec un titre invalide."""
    # Configurer le mock pour simuler qu'aucune piste n'existe
    mock_query = MagicMock()
    mock_query.filter.return_value.filter.return_value.first.return_value = None
    db_session.query.return_value = mock_query

    # Configurer le mock pour simuler la création d'une nouvelle piste
    def side_effect_add(track):
        track.id = 3
        assert track.title == "Unknown Track"

    db_session.add.side_effect = side_effect_add

    # Appeler la méthode à tester avec un titre invalide
    track = await track_creator.get_or_create_track(
        title="", artist_id=1, album="Test Album"  # Titre invalide
    )

    # Vérifier les résultats
    assert track.title == "Unknown Track"
    assert track.id == 3

    # Vérifier les appels de méthode
    db_session.query.assert_called_once_with(Track)
    db_session.add.assert_called_once()
    db_session.commit.assert_called_once()


def test_validate_track_data_complete(track_creator):
    """Teste la validation de données de piste complètes."""
    # Données de piste complètes
    track_data = {
        "title": "Test Track",
        "artist": "Test Artist",
        "album": "Test Album",
        "isrc": "ABCDE1234567",
        "label": "Test Label",
        "release_date": "2023-01-01",
        "duration": 180.5,
    }

    # Appeler la méthode à tester
    result = track_creator.validate_track_data(track_data)

    # Vérifier les résultats
    assert result["title"] == "Test Track"
    assert result["artist"] == "Test Artist"
    assert result["album"] == "Test Album"
    assert result["isrc"] == "ABCDE1234567"
    assert result["label"] == "Test Label"
    assert result["release_date"] == "2023-01-01"
    assert result["duration"] == 180.5


def test_validate_track_data_missing_fields(track_creator):
    """Teste la validation de données de piste avec des champs manquants."""
    # Données de piste avec des champs manquants
    track_data = {"title": "Test Track", "artist": "Test Artist"}

    # Appeler la méthode à tester
    result = track_creator.validate_track_data(track_data)

    # Vérifier les résultats
    assert result["title"] == "Test Track"
    assert result["artist"] == "Test Artist"
    assert result.get("album") is None
    assert result.get("isrc") is None
    assert result.get("label") is None
    assert result.get("release_date") is None
    assert result.get("duration") is None


def test_validate_track_data_normalize_isrc(track_creator):
    """Teste la normalisation de l'ISRC lors de la validation des données."""
    # Données de piste avec un ISRC non normalisé
    track_data = {
        "title": "Test Track",
        "artist": "Test Artist",
        "isrc": "abcde-1234-567",  # ISRC non normalisé
    }

    # Appeler la méthode à tester
    result = track_creator.validate_track_data(track_data)

    # Vérifier les résultats
    assert result["isrc"] == "ABCDE1234567"  # ISRC normalisé


if __name__ == "__main__":
    pytest.main()
