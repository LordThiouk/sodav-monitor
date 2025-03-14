"""
Tests pour la contrainte d'unicité ISRC.

Ce module contient des tests pour vérifier que la contrainte d'unicité
sur la colonne ISRC de la table tracks fonctionne correctement.
"""

import unittest
import uuid
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from backend.detection.audio_processor.track_manager import TrackManager
from backend.models.database import get_db
from backend.models.models import Artist, StationTrackStats, Track, TrackDetection


class TestISRCUniqueness(unittest.TestCase):
    """Tests pour vérifier la contrainte d'unicité sur la colonne ISRC de la table tracks."""

    def setUp(self):
        """Initialiser la base de données pour les tests."""
        # Obtenir une session de base de données
        self.db_session = next(get_db())

        # Créer un artiste de test avec un nom unique
        unique_name = f"Test Artist {uuid.uuid4()}"
        self.artist = Artist(name=unique_name)
        self.db_session.add(self.artist)
        self.db_session.commit()

        # Générer un ISRC unique pour ce test
        self.unique_isrc = f"FR{uuid.uuid4().hex[:10].upper()}"

        # Initialiser le gestionnaire de pistes
        self.track_manager = TrackManager(self.db_session)

    def tearDown(self):
        """Nettoyer la base de données après chaque test."""
        try:
            # Supprimer d'abord les statistiques de pistes
            self.db_session.query(StationTrackStats).delete()

            # Supprimer toutes les détections
            self.db_session.query(TrackDetection).delete()

            # Supprimer toutes les pistes
            self.db_session.query(Track).delete()

            # Supprimer l'artiste de test
            self.db_session.query(Artist).filter(Artist.id == self.artist.id).delete()

            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            print(f"Erreur lors du nettoyage: {e}")

    def test_isrc_uniqueness_constraint(self):
        """Tester que la contrainte d'unicité ISRC est appliquée."""
        # Créer une première piste avec un ISRC
        track1 = Track(
            title="Test Track 1",
            artist_id=self.artist.id,
            isrc=self.unique_isrc,
            label="Test Label",
            album="Test Album",
        )
        self.db_session.add(track1)
        self.db_session.commit()

        # Tenter de créer une deuxième piste avec le même ISRC
        track2 = Track(
            title="Test Track 2",
            artist_id=self.artist.id,
            isrc=self.unique_isrc,
            label="Another Label",
            album="Another Album",
        )
        self.db_session.add(track2)

        # Vérifier que la contrainte d'unicité est appliquée
        with self.assertRaises(IntegrityError):
            self.db_session.commit()

        # Rollback pour nettoyer la session
        self.db_session.rollback()

    def test_find_track_by_isrc(self):
        """Tester la recherche d'une piste par ISRC."""
        # Créer une piste avec un ISRC unique
        test_isrc = f"FR{uuid.uuid4().hex[:10].upper()}"
        track = Track(
            title="Test Track",
            artist_id=self.artist.id,
            isrc=test_isrc,
            label="Test Label",
            album="Test Album",
        )
        self.db_session.add(track)
        self.db_session.commit()

        # Rechercher la piste par ISRC
        found_track = self.db_session.query(Track).filter(Track.isrc == test_isrc).first()

        # Vérifier que la piste est trouvée
        self.assertIsNotNone(found_track)
        self.assertEqual(found_track.title, "Test Track")
        self.assertEqual(found_track.isrc, test_isrc)

    async def test_acoustid_match_with_isrc(self):
        """Tester que la méthode find_acoustid_match utilise l'ISRC pour trouver des pistes existantes."""
        # Créer une piste avec un ISRC unique
        test_isrc = f"FR{uuid.uuid4().hex[:10].upper()}"
        track = Track(
            title="Test Track",
            artist_id=self.artist.id,
            isrc=test_isrc,
            label="Test Label",
            album="Test Album",
        )
        self.db_session.add(track)
        self.db_session.commit()

        # Simuler des caractéristiques audio
        audio_features = {
            "duration": 180,
            "fingerprint": "test_fingerprint",
            "fingerprint_raw": "test_fingerprint_raw",
        }

        # Simuler un résultat AcoustID avec le même ISRC
        acoustid_result = {
            "recordings": [
                {
                    "isrc": [test_isrc],
                    "title": "Different Title",
                    "artists": [{"name": "Different Artist"}],
                }
            ]
        }

        # Appeler la méthode find_acoustid_match
        result = await self.track_manager.find_acoustid_match(
            audio_features, acoustid_result, station_id=1
        )

        # Vérifier que la piste existante est trouvée
        self.assertIsNotNone(result)
        self.assertIn("track", result)
        self.assertEqual(result["track"]["id"], track.id)
        self.assertEqual(result["track"]["title"], "Test Track")
        self.assertEqual(
            result["confidence"], 1.0
        )  # Confiance maximale pour une correspondance ISRC

    async def test_audd_match_with_isrc(self):
        """Tester que la méthode find_audd_match utilise l'ISRC pour trouver des pistes existantes."""
        # Créer une piste avec un ISRC unique
        test_isrc = f"FR{uuid.uuid4().hex[:10].upper()}"
        track = Track(
            title="Test Track",
            artist_id=self.artist.id,
            isrc=test_isrc,
            label="Test Label",
            album="Test Album",
        )
        self.db_session.add(track)
        self.db_session.commit()

        # Simuler des caractéristiques audio
        audio_features = {
            "duration": 180,
            "fingerprint": "test_fingerprint",
            "fingerprint_raw": "test_fingerprint_raw",
        }

        # Simuler un résultat AudD avec le même ISRC
        audd_result = {
            "result": {
                "isrc": test_isrc,
                "title": "Different Title",
                "artist": "Different Artist",
                "album": "Different Album",
                "label": "Different Label",
            }
        }

        # Appeler la méthode find_audd_match
        result = await self.track_manager.find_audd_match(audio_features, audd_result, station_id=1)

        # Vérifier que la piste existante est trouvée
        self.assertIsNotNone(result)
        self.assertIn("track", result)
        self.assertEqual(result["track"]["id"], track.id)
        self.assertEqual(result["track"]["title"], "Test Track")
        self.assertEqual(
            result["confidence"], 1.0
        )  # Confiance maximale pour une correspondance ISRC

    def test_update_play_statistics(self):
        """Tester que les statistiques de lecture sont mises à jour pour les pistes existantes."""
        # Créer une piste avec un ISRC unique
        test_isrc = f"FR{uuid.uuid4().hex[:10].upper()}"
        track = Track(
            title="Test Track",
            artist_id=self.artist.id,
            isrc=test_isrc,
            label="Test Label",
            album="Test Album",
        )
        self.db_session.add(track)
        self.db_session.commit()

        # Créer une station pour les statistiques
        station_id = 1  # Utiliser un ID numérique pour correspondre au modèle

        # Utiliser la méthode _record_play_time pour enregistrer une détection et mettre à jour les statistiques
        self.track_manager._record_play_time(station_id, track.id, 60)  # 60 secondes

        # Vérifier que les statistiques sont créées
        stats = (
            self.db_session.query(StationTrackStats)
            .filter(
                StationTrackStats.track_id == track.id, StationTrackStats.station_id == station_id
            )
            .first()
        )

        self.assertIsNotNone(stats)
        self.assertEqual(stats.play_count, 1)
        self.assertEqual(stats.total_play_time.total_seconds(), 60)

        # Enregistrer une deuxième détection
        self.track_manager._record_play_time(station_id, track.id, 120)  # 120 secondes

        # Vérifier que les statistiques sont mises à jour
        stats = (
            self.db_session.query(StationTrackStats)
            .filter(
                StationTrackStats.track_id == track.id, StationTrackStats.station_id == station_id
            )
            .first()
        )

        self.assertIsNotNone(stats)
        self.assertEqual(stats.play_count, 2)
        self.assertEqual(stats.total_play_time.total_seconds(), 180)  # 60 + 120 = 180 secondes


if __name__ == "__main__":
    unittest.main()
