"""Tests pour le module radio."""

import os
import logging
import requests
import time
import io
from pydub import AudioSegment
import pytest
from sqlalchemy.orm import Session
from ..audio_processor import AudioProcessor
from ..models.models import RadioStation, Track, TrackDetection
from ..models.database import SessionLocal
from ..utils.radio_manager import RadioManager
from ..utils.fingerprint import generate_fingerprint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    """Configuration pour les tests."""
    MAX_RETRIES = 3
    REQUEST_TIMEOUT = 10
    CHUNK_SIZE = 8192
    MAX_AUDIO_LENGTH = 30
    ACOUSTID_API_KEY = os.getenv("ACOUSTID_API_KEY", "test_key")
    AUDD_API_KEY = os.getenv("AUDD_API_KEY", "test_key")

def create_session():
    """Create a requests session with proper headers"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    # Configure retries
    retries = requests.adapters.Retry(
        total=Config.MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount('http://', requests.adapters.HTTPAdapter(max_retries=retries))
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))
    return session

def record_stream(url: str, duration: int = None) -> bytes:
    """Record audio from a stream URL"""
    if duration is None:
        duration = Config.MAX_AUDIO_LENGTH
        
    session = create_session()
    
    try:
        # Test connection first with a HEAD request
        logger.info(f"Testing connection to {url}...")
        try:
            session.head(url, timeout=Config.REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            logger.warning(f"HEAD request failed: {str(e)}, trying GET...")
            # If HEAD is not supported, try GET
            session.get(url, stream=True, timeout=Config.REQUEST_TIMEOUT)
        
        # Now start the actual recording
        logger.info(f"Connected to stream, recording {duration} seconds...")
        response = session.get(url, stream=True, timeout=10)  # Set a timeout of 10 seconds
        
        response.raise_for_status()
        
        # Record audio
        chunks = []
        start_time = time.time()
        bytes_recorded = 0
        last_chunk_time = start_time
        
        for chunk in response.iter_content(chunk_size=Config.CHUNK_SIZE):
            current_time = time.time()
            if current_time - start_time > duration:
                logger.info("Recording duration reached")
                break
                
            if current_time - last_chunk_time > Config.REQUEST_TIMEOUT:
                raise Exception(f"Stream timeout - no data received for {Config.REQUEST_TIMEOUT} seconds")
                
            if chunk:
                chunks.append(chunk)
                bytes_recorded += len(chunk)
                last_chunk_time = current_time
                if bytes_recorded % (Config.CHUNK_SIZE * 10) == 0:
                    logger.info(f"Recorded {bytes_recorded/1024:.1f}KB...")
        
        total_time = time.time() - start_time
        logger.info(f"Finished recording {bytes_recorded/1024:.1f}KB in {total_time:.1f} seconds")
        
        if not chunks:
            raise Exception("No data received from stream")
            
        if bytes_recorded < Config.CHUNK_SIZE * 10:
            raise Exception(f"Not enough data received: {bytes_recorded} bytes")
        
        # Convert to proper audio format
        logger.info("Converting audio data...")
        audio_data = b''.join(chunks)
        audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
        logger.info(f"Audio properties: {audio.channels} channels, {audio.frame_rate}Hz, {len(audio)}ms duration")
        
        # Export as MP3 with good quality
        logger.info("Exporting audio...")
        output = io.BytesIO()
        audio.export(output, format="mp3", bitrate="192k")
        logger.info("Audio converted and ready for processing")
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error recording stream: {str(e)}")
        raise
    finally:
        session.close()

def test_stream(url: str, duration: int = None) -> dict:
    """Test a radio stream for music detection"""
    if duration is None:
        duration = Config.MAX_AUDIO_LENGTH
        
    logger.info(f"Testing stream: {url}")
    
    try:
        # Record audio from stream
        logger.info(f"Recording {duration} seconds of audio...")
        try:
            session = create_session()
            response = session.get(url, stream=True, timeout=10)  # Set a timeout of 10 seconds
            response.raise_for_status()
            audio_data = response.content  # Get the audio data from the stream
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching audio stream: {str(e)}")
            return {
                "url": url,
                "duration": duration,
                "error": str(e)
            }
        
        if len(audio_data) < Config.CHUNK_SIZE:
            raise Exception("Not enough audio data recorded")
        
        # Process audio
        processor = AudioProcessor(
            acoustid_api_key=Config.ACOUSTID_API_KEY,
            audd_api_key=Config.AUDD_API_KEY
        )
        
        logger.info("Starting music detection...")
        result = processor.detect_track(audio_data)
        
        if "error" in result:
            logger.error(f"Music detection failed: {result['error']}")
        else:
            logger.info("Music detection results:")
            logger.info(f"Title: {result.get('title', 'Unknown')}")
            logger.info(f"Artist: {result.get('artist', 'Unknown')}")
            logger.info(f"Confidence: {result.get('confidence', 0)}%")
            logger.info(f"Service: {result.get('service', 'Unknown')}")
        
        return {
            "url": url,
            "duration": duration,
            "detection_result": result
        }
        
    except Exception as e:
        logger.error(f"Error testing stream: {str(e)}")
        return {
            "url": url,
            "duration": duration,
            "error": str(e)
        }

def format_detection_results(results: dict) -> str:
    """Format detection results for display"""
    output = []
    
    if "error" in results:
        output.append(f"Error: {results['error']}")
        return "\n".join(output)
    
    detection = results.get("detection_result", {})
    
    # Show music/speech detection results with timestamp
    current_time = time.strftime("%H:%M:%S")
    if detection.get("is_music", False):
        output.append(f"\n[{current_time}] Music detected")
    else:
        output.append(f"\n[{current_time}] Speech detected")
    
    # Show confidence
    output.append(f"Confidence: {detection.get('confidence', 0):.2f}%")
    
    # If music was detected with high confidence, show track info
    track_info = detection.get("track_info", {})
    if track_info and "error" not in track_info:
        output.extend([
            "\nTrack Information:",
            f"Recognition Service: {track_info.get('service', 'Unknown').upper()}",
            f"Title: {track_info.get('title', 'Unknown')}",
            f"Artist: {track_info.get('artist', 'Unknown')}",
            f"Album: {track_info.get('album', 'Unknown')}"
        ])
        
        # Show year or release date
        if track_info.get('year'):
            output.append(f"Year: {track_info['year']}")
        elif track_info.get('release_date'):
            output.append(f"Release Date: {track_info['release_date']}")
        
        # Show ISRC if available
        if track_info.get('isrc'):
            output.append(f"ISRC: {track_info['isrc']}")
        
        # Show streaming links if available
        additional_data = track_info.get('additional_data', {})
        if additional_data:
            output.append("\nStreaming Links:")
            if additional_data.get('spotify'):
                output.append(f"Spotify: {additional_data['spotify'].get('external_urls', {}).get('spotify', 'N/A')}")
            if additional_data.get('apple_music'):
                output.append(f"Apple Music: {additional_data['apple_music'].get('url', 'N/A')}")
            if additional_data.get('deezer'):
                output.append(f"Deezer: {additional_data['deezer'].get('link', 'N/A')}")
    
    # Show detailed audio analysis
    output.extend([
        "\nAudio Analysis:",
        "Frequency Distribution:",
        f"  Bass: {detection.get('analysis', {}).get('frequency_distribution', {}).get('low', 0):.1f}%",
        f"  Mids: {detection.get('analysis', {}).get('frequency_distribution', {}).get('mid', 0):.1f}%",
        f"  Highs: {detection.get('analysis', {}).get('frequency_distribution', {}).get('high', 0):.1f}%",
        f"Rhythm Strength: {detection.get('analysis', {}).get('rhythm_strength', 0):.1f}%",
        f"Quality: {detection.get('analysis', {}).get('audio_quality', {}).get('sample_rate', 0)/1000:.1f}kHz, "
        f"{detection.get('analysis', {}).get('audio_quality', {}).get('channels', 0)} channels"
    ])
    
    return "\n".join(output)

@pytest.fixture
def url():
    return "http://listen.senemultimedia.net:8090/stream"  # Valid stream URL

def test_radio_detection(url):
    try:
        response = requests.get(url, stream=True, timeout=10)  # Set a timeout of 10 seconds
        audio_data = response.content  # Get the audio data from the stream
        processor = AudioProcessor(
            acoustid_api_key=Config.ACOUSTID_API_KEY,
            audd_api_key=Config.AUDD_API_KEY
        )
        detection_result = processor.detect_track(audio_data)  # Use the fingerprinter to detect music
        print(detection_result)
    except Exception as e:
        print(f"Error detecting music: {e}")

def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("Testing Sene Multimedia")
    logger.info("=" * 60)
    
    # Test streams
    streams = [
        "http://listen.senemultimedia.net:8090/stream"
    ]
    
    for stream_url in streams:
        try:
            result = test_stream(stream_url, Config.MAX_AUDIO_LENGTH)
            logger.info(f"\nResults for {stream_url}:")
            if "error" in result:
                logger.error(f"Test failed: {result['error']}")
            else:
                detection = result["detection_result"]
                if "error" in detection:
                    logger.warning(f"No music detected: {detection['error']}")
                else:
                    logger.info(f"Music detected!")
                    logger.info(f"Title: {detection.get('title', 'Unknown')}")
                    logger.info(f"Artist: {detection.get('artist', 'Unknown')}")
                    logger.info(f"Confidence: {detection.get('confidence', 0)}%")
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
        
        logger.info("-" * 60)

if __name__ == "__main__":
    test_radio_detection(url="http://listen.senemultimedia.net:8090/stream")  # Call the function to test music detection
    main()

@pytest.fixture(scope="function")
def db_session() -> Session:
    """Fixture pour la session de base de données de test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def audio_processor():
    """Fixture pour le processeur audio."""
    return AudioProcessor()

@pytest.fixture
def test_station(db_session):
    """Fixture pour une station de test."""
    station = RadioStation(
        name="Test Radio",
        stream_url="http://test.stream/audio",
        country="SN",
        language="fr",
        is_active=True
    )
    db_session.add(station)
    db_session.commit()
    return station

@pytest.fixture
def test_track(db_session):
    """Fixture pour une piste de test."""
    track = Track(
        title="Test Track",
        artist="Test Artist",
        duration=180,
        fingerprint=b"test_fingerprint"
    )
    db_session.add(track)
    db_session.commit()
    return track

def test_audio_processor_initialization(audio_processor):
    """Test de l'initialisation du processeur audio."""
    assert audio_processor is not None
    assert hasattr(audio_processor, "process_stream")
    assert hasattr(audio_processor, "extract_features")

@pytest.mark.asyncio
async def test_process_stream(audio_processor, test_station):
    """Test du traitement du flux audio."""
    result = await audio_processor.process_stream(test_station.stream_url)
    assert result is not None
    assert "features" in result
    assert "confidence" in result

def test_track_detection(db_session, test_station, test_track):
    """Test de la détection de piste."""
    detection = TrackDetection(
        station_id=test_station.id,
        track_id=test_track.id,
        confidence=0.95,
        play_duration=180
    )
    db_session.add(detection)
    db_session.commit()
    
    saved_detection = db_session.query(TrackDetection).first()
    assert saved_detection.station_id == test_station.id
    assert saved_detection.track_id == test_track.id
    assert saved_detection.confidence == 0.95

@pytest.fixture
def radio_manager(db_session):
    """Fixture pour le gestionnaire radio."""
    return RadioManager(db_session)

def test_generate_fingerprint():
    """Test de la génération d'empreintes audio."""
    # Simuler un échantillon audio
    audio_sample = b"test_audio_data"
    fingerprint = generate_fingerprint(audio_sample)
    assert fingerprint is not None
    assert isinstance(fingerprint, bytes)

def test_radio_station_creation(db_session, test_station):
    """Test de la création d'une station radio."""
    assert test_station.id is not None
    assert test_station.name == "Test Radio"
    assert test_station.is_active == True

def test_track_detection(db_session, test_station):
    """Test de la détection de pistes."""
    # Créer une piste
    track = Track(
        title="Test Track",
        artist="Test Artist",
        duration=180
    )
    db_session.add(track)
    db_session.commit()

    # Créer une détection
    detection = TrackDetection(
        station_id=test_station.id,
        track_id=track.id,
        confidence=0.95,
        play_duration=180
    )
    db_session.add(detection)
    db_session.commit()

    # Vérifier la détection
    assert detection.id is not None
    assert detection.confidence > 0.9
    assert detection.station_id == test_station.id
    assert detection.track_id == track.id

def test_stream(radio_manager, test_station):
    """Test de traitement du flux audio."""
    try:
        # Simuler des données audio
        audio_data = os.urandom(Config.CHUNK_SIZE * 10)  # Données aléatoires pour le test
        
        # Créer un processeur audio avec des clés de test
        processor = AudioProcessor()
        
        # Traiter les données
        is_music, confidence = processor.process_stream(audio_data)
        
        # Vérifier les résultats
        assert isinstance(is_music, bool)
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1
        
    except Exception as e:
        pytest.fail(f"Test failed: {str(e)}")

def test_radio_detection(radio_manager, test_station):
    """Test de détection de musique."""
    try:
        # Simuler une détection
        features = generate_fingerprint(os.urandom(Config.CHUNK_SIZE * 10))
        assert len(features) > 0
        
        # Créer une piste de test
        track = Track(
            title="Test Track",
            artist="Test Artist",
            fingerprint=features.tobytes()
        )
        radio_manager.db.add(track)
        radio_manager.db.commit()
        
        # Vérifier que la piste est bien créée
        assert track.id is not None
        
        # Créer une détection
        detection = TrackDetection(
            station_id=test_station.id,
            track_id=track.id,
            confidence=0.85
        )
        radio_manager.db.add(detection)
        radio_manager.db.commit()
        
        # Vérifier la détection
        assert detection.id is not None
        assert detection.confidence == 0.85
        assert detection.station_id == test_station.id
        assert detection.track_id == track.id
        
    except Exception as e:
        pytest.fail(f"Test failed: {str(e)}")
