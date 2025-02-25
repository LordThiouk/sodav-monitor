import asyncio
import logging
from sqlalchemy.orm import Session
from models import RadioStation, Track, TrackDetection
from radio_manager import RadioManager
from audio_processor import AudioProcessor
from main import SessionLocal, engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_radio_browser():
    """Test fetching radio stations from RadioBrowser API"""
    try:
        db = SessionLocal()
        radio_manager = RadioManager(db)
        
        # Fetch Senegalese radio stations
        logger.info("Fetching Senegalese radio stations...")
        await radio_manager.update_station_list(country="Senegal")
        
        # Get active stations
        stations = await radio_manager.get_active_stations()
        logger.info(f"Found {len(stations)} active stations")
        
        for station in stations:
            logger.info(f"Station: {station.name} ({station.stream_url})")
            
            # Test stream availability
            is_available = await radio_manager.check_station_availability(station)
            logger.info(f"Stream available: {is_available}")
            
        db.close()
        return stations
        
    except Exception as e:
        logger.error(f"Error testing radio browser: {str(e)}")
        return []

async def test_audio_processing(stations):
    """Test audio processing and track detection"""
    try:
        db = SessionLocal()
        audio_processor = AudioProcessor(db)
        
        # Add a test track
        test_track = Track(
            title="Test Track",
            artist="Test Artist",
            fingerprint="1234,5678,9012",  # This is just a test fingerprint
            fingerprint_hash="abcd1234"
        )
        db.add(test_track)
        db.commit()
        
        # Process first available stream
        for station in stations:
            logger.info(f"Testing audio processing for station: {station.name}")
            try:
                await audio_processor.process_stream(station)
                break  # Process only one station for testing
            except Exception as e:
                logger.error(f"Error processing station {station.name}: {str(e)}")
                continue
        
        # Check detections
        detections = db.query(TrackDetection).all()
        logger.info(f"Found {len(detections)} track detections")
        
        for detection in detections:
            logger.info(
                f"Detected track '{detection.track.title}' on {detection.station.name} "
                f"with {detection.confidence*100:.1f}% confidence"
            )
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error testing audio processing: {str(e)}")

async def main():
    """Main test function"""
    logger.info("Starting system test...")
    
    # Test radio browser
    stations = await test_radio_browser()
    
    if stations:
        # Test audio processing
        await test_audio_processing(stations)
    
    logger.info("System test completed")

if __name__ == "__main__":
    asyncio.run(main())
