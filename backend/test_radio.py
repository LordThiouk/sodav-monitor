import os
import logging
import requests
import time
import io
from pydub import AudioSegment
from fingerprint import AudioProcessor
from config import Config
import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
