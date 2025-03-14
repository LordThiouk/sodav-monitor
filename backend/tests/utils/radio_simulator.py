"""
Simulateur de station de radio pour les tests.

Ce module fournit un serveur HTTP qui diffuse des fichiers audio en continu,
simulant une station de radio réelle pour les tests du système de détection.
"""

import asyncio
import io
import logging
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pydub
from pydub import AudioSegment

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("radio_simulator")

# Constantes
CHUNK_SIZE = 8192  # Taille des chunks audio en octets
AUDIO_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "audio" / "senegal"
DEFAULT_PORT = 8765
DEFAULT_BITRATE = "128k"  # Débit binaire par défaut pour le streaming


class RadioStation:
    """Représente une station de radio simulée avec sa playlist."""

    def __init__(self, name: str, playlist: List[Path], port: int = DEFAULT_PORT):
        """
        Initialise une station de radio simulée.

        Args:
            name: Nom de la station
            playlist: Liste des chemins vers les fichiers audio
            port: Port sur lequel la station diffusera
        """
        self.name = name
        self.playlist = playlist
        self.port = port
        self.current_track_index = 0
        self.current_track: Optional[Path] = None
        self.current_track_start_time: Optional[float] = None
        self.current_track_duration: Optional[float] = None
        self.is_running = False
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.track_change_callbacks = []
        self.track_info: Dict[Path, Dict] = {}  # Stocke les informations sur les pistes

    def start(self) -> None:
        """Démarre la diffusion de la station de radio."""
        if self.is_running:
            logger.warning(f"La station {self.name} est déjà en cours d'exécution")
            return

        # Analyser les informations des pistes à l'avance
        self._analyze_tracks()

        # Configurer le gestionnaire de requêtes HTTP
        handler = self._create_request_handler()

        # Créer et démarrer le serveur HTTP
        self.server = HTTPServer(("localhost", self.port), handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        self.is_running = True
        logger.info(f"Station {self.name} démarrée sur http://localhost:{self.port}")

        # Démarrer la lecture de la première piste
        self._play_next_track()

    def stop(self) -> None:
        """Arrête la diffusion de la station de radio."""
        if not self.is_running:
            logger.warning(f"La station {self.name} n'est pas en cours d'exécution")
            return

        if self.server:
            self.server.shutdown()
            self.server.server_close()

        self.is_running = False
        self.current_track = None
        self.current_track_start_time = None
        logger.info(f"Station {self.name} arrêtée")

    def add_track_change_callback(self, callback) -> None:
        """
        Ajoute un callback qui sera appelé lorsqu'une piste change.

        Args:
            callback: Fonction à appeler avec (station_name, track_path, start_time)
        """
        self.track_change_callbacks.append(callback)

    def get_current_track_info(self) -> Dict:
        """
        Retourne les informations sur la piste en cours de lecture.

        Returns:
            Dictionnaire contenant les informations sur la piste en cours
        """
        if not self.current_track:
            return {"status": "idle", "station": self.name}

        elapsed = time.time() - self.current_track_start_time
        return {
            "status": "playing",
            "station": self.name,
            "track": self.current_track.name,
            "start_time": self.current_track_start_time,
            "elapsed": elapsed,
            "duration": self.current_track_duration,
            "remaining": max(0, self.current_track_duration - elapsed),
        }

    def _analyze_tracks(self) -> None:
        """Analyse les pistes audio pour extraire leur durée et d'autres informations."""
        for track_path in self.playlist:
            if track_path in self.track_info:
                continue  # Déjà analysé

            try:
                audio = AudioSegment.from_file(track_path)
                self.track_info[track_path] = {
                    "duration": audio.duration_seconds,
                    "channels": audio.channels,
                    "sample_width": audio.sample_width,
                    "frame_rate": audio.frame_rate,
                }
                logger.info(
                    f"Analysé: {track_path.name} - Durée: {audio.duration_seconds:.2f}s, "
                    f"Taux: {audio.frame_rate}Hz"
                )
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse de {track_path}: {e}")
                # Ajouter des valeurs par défaut
                self.track_info[track_path] = {
                    "duration": 180.0,  # 3 minutes par défaut
                    "channels": 2,
                    "sample_width": 2,
                    "frame_rate": 44100,
                }

    def _play_next_track(self) -> None:
        """Passe à la piste suivante dans la playlist."""
        if not self.is_running or not self.playlist:
            return

        # Sélectionner la piste suivante
        self.current_track = self.playlist[self.current_track_index]
        self.current_track_index = (self.current_track_index + 1) % len(self.playlist)
        self.current_track_start_time = time.time()
        self.current_track_duration = self.track_info[self.current_track]["duration"]

        # Notifier les callbacks
        for callback in self.track_change_callbacks:
            try:
                callback(self.name, self.current_track, self.current_track_start_time)
            except Exception as e:
                logger.error(f"Erreur dans le callback de changement de piste: {e}")

        logger.info(
            f"Lecture de {self.current_track.name} - " f"Durée: {self.current_track_duration:.2f}s"
        )

        # Planifier le changement de piste
        threading.Timer(self.current_track_duration, self._play_next_track).start()

    def _create_request_handler(self):
        """Crée un gestionnaire de requêtes HTTP pour diffuser l'audio."""
        station = self  # Référence à l'instance actuelle pour l'utiliser dans le handler

        class RadioStreamHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                """Gère les requêtes GET pour diffuser l'audio."""
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()

                try:
                    while station.is_running:
                        if not station.current_track:
                            time.sleep(0.1)
                            continue

                        # Obtenir le fichier audio actuel
                        current_track = station.current_track

                        try:
                            # Charger l'audio
                            audio = AudioSegment.from_file(current_track)

                            # Convertir en MP3 pour le streaming avec un bitrate plus bas pour les tests
                            mp3_data = io.BytesIO()
                            audio.export(
                                mp3_data, format="mp3", bitrate="64k"
                            )  # Bitrate réduit pour les tests
                            mp3_data.seek(0)

                            # Envoyer les données par morceaux
                            while station.current_track == current_track and station.is_running:
                                chunk = mp3_data.read(CHUNK_SIZE)
                                if not chunk:
                                    break

                                try:
                                    # Envoyer le chunk en format chunked HTTP
                                    chunk_size = len(chunk)
                                    self.wfile.write(f"{chunk_size:X}\r\n".encode())
                                    self.wfile.write(chunk)
                                    self.wfile.write(b"\r\n")
                                    self.wfile.flush()

                                    # Pause plus courte pour accélérer le streaming en test
                                    time.sleep(0.05)
                                except (BrokenPipeError, ConnectionResetError) as e:
                                    # Client déconnecté, sortir de la boucle
                                    logger.debug(f"Client déconnecté pendant la diffusion: {e}")
                                    return
                                except Exception as e:
                                    logger.error(f"Erreur pendant l'envoi du chunk: {e}")
                                    return

                        except Exception as e:
                            # Gérer les erreurs de diffusion de manière plus silencieuse
                            if not isinstance(e, (BrokenPipeError, ConnectionResetError)):
                                logger.error(f"Erreur lors de la diffusion de {current_track}: {e}")
                            time.sleep(1)  # Pause avant de réessayer

                except (BrokenPipeError, ConnectionResetError):
                    # Client déconnecté
                    logger.debug("Client déconnecté")
                except Exception as e:
                    logger.error(f"Erreur de streaming: {e}")

            def log_message(self, format, *args):
                """Surcharge pour utiliser notre logger."""
                if args[1] == "200":  # Supprimer les logs de succès pour réduire le bruit
                    return
                logger.info(f"{self.address_string()} - {format % args}")

        return RadioStreamHandler


class RadioSimulator:
    """Gestionnaire de simulation de stations de radio."""

    def __init__(self):
        """Initialise le simulateur de stations de radio."""
        self.stations: Dict[str, RadioStation] = {}
        self.base_port = DEFAULT_PORT

    def create_station(self, name: str, audio_dir: Optional[Path] = None) -> RadioStation:
        """
        Crée une nouvelle station de radio simulée.

        Args:
            name: Nom de la station
            audio_dir: Répertoire contenant les fichiers audio (utilise le répertoire par défaut si None)

        Returns:
            Instance de RadioStation créée
        """
        # Déterminer le répertoire audio
        if audio_dir is None:
            audio_dir = AUDIO_DIR

        # Vérifier que le répertoire existe
        if not audio_dir.exists():
            logger.warning(f"Le répertoire {audio_dir} n'existe pas. Création...")
            os.makedirs(audio_dir, exist_ok=True)

        # Trouver tous les fichiers audio dans le répertoire
        audio_files = []
        for ext in ["*.mp3", "*.wav", "*.ogg", "*.m4a", "*.flac"]:
            audio_files.extend(list(audio_dir.glob(ext)))

        if not audio_files:
            logger.warning(f"Aucun fichier audio trouvé dans {audio_dir}")
            return None

        # Mélanger la playlist
        random.shuffle(audio_files)

        # Attribuer un port unique
        port = self.base_port + len(self.stations)

        # Créer la station
        station = RadioStation(name, audio_files, port)
        self.stations[name] = station
        logger.info(f"Station {name} créée avec {len(audio_files)} pistes sur le port {port}")

        return station

    def start_all(self) -> None:
        """Démarre toutes les stations de radio."""
        for name, station in self.stations.items():
            station.start()

    def stop_all(self) -> None:
        """Arrête toutes les stations de radio."""
        for name, station in self.stations.items():
            station.stop()

    def get_station_urls(self) -> Dict[str, str]:
        """
        Retourne les URLs de streaming pour toutes les stations.

        Returns:
            Dictionnaire {nom_station: url_streaming}
        """
        return {name: f"http://localhost:{station.port}" for name, station in self.stations.items()}


# Fonction utilitaire pour télécharger des fichiers audio de test
def download_test_audio(
    url: str, output_dir: Path = AUDIO_DIR, filename: Optional[str] = None
) -> Path:
    """
    Télécharge un fichier audio de test.

    Args:
        url: URL du fichier audio à télécharger
        output_dir: Répertoire de sortie
        filename: Nom du fichier de sortie (utilise le nom du fichier dans l'URL si None)

    Returns:
        Chemin vers le fichier téléchargé
    """
    from urllib.parse import urlparse

    import requests

    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)

    # Déterminer le nom du fichier
    if filename is None:
        filename = os.path.basename(urlparse(url).path)
        if not filename:
            filename = f"audio_{int(time.time())}.mp3"

    output_path = output_dir / filename

    # Télécharger le fichier
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Fichier téléchargé: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Erreur lors du téléchargement de {url}: {e}")
        return None


# Exemple d'utilisation
if __name__ == "__main__":
    # Créer le simulateur
    simulator = RadioSimulator()

    # Créer une station
    station = simulator.create_station("Radio Dakar")

    if station and station.playlist:
        # Démarrer la station
        station.start()

        # Afficher l'URL de streaming
        print(f"Station {station.name} disponible sur http://localhost:{station.port}")

        try:
            # Maintenir le programme en cours d'exécution
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # Arrêter la station à la sortie
            station.stop()
            print("Station arrêtée")
    else:
        print("Impossible de créer la station: aucun fichier audio trouvé")
        print(f"Veuillez ajouter des fichiers audio dans {AUDIO_DIR}")
