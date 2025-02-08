import requests
import json
from datetime import datetime
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_feature_value(value):
    """Format feature values for display"""
    if isinstance(value, float):
        if value < 0.01:
            return f"{value:.2e}"
        return f"{value:.2f}"
    return str(value)

def print_separator(char="-", length=60):
    print(char * length)

def test_detection():
    url = "http://localhost:8000/api/detect"
    data = {
        "stream_url": "https://stream.zeno.fm/b38a68a1krquv"
    }
    
    try:
        print("\n🎵 SODAV Music Monitor - Live Detection")
        print_separator("=")
        print(f"Stream URL: {data['stream_url']}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_separator()
        print("Recording audio... Please wait 10 seconds")
        
        start_time = datetime.now()
        logger.info(f"Making request to {url} with data: {data}")
        response = requests.post(url, json=data)
        logger.info(f"Response status code: {response.status_code}")
        
        print(f"\nStatus: {'✅ Success' if response.status_code == 200 else '❌ Failed'}")
        print(f"Response time: {(datetime.now() - start_time).total_seconds():.2f}s")
        print_separator()
        
        result = response.json()
        logger.debug(f"Raw response: {json.dumps(result, indent=2)}")
        
        if "error" not in result:
            # Audio Analysis Section
            if "audio_features" in result:
                print("\n📊 Audio Analysis")
                print_separator("-")
                features = result["audio_features"]
                print(f"Music Probability: {format_feature_value(features.get('music_likelihood', 0))}%")
                print("\nAudio Characteristics:")
                print(f"- Spectral Centroid: {format_feature_value(features.get('spectral_centroid_mean', 0))} Hz")
                print(f"- Energy Variation: {format_feature_value(features.get('rms_energy_std', 0))}")
                print(f"- Zero Crossing Rate: {format_feature_value(features.get('zero_crossing_rate_mean', 0))}")
                print(f"- Spectral Rolloff: {format_feature_value(features.get('spectral_rolloff_mean', 0))} Hz")
                print_separator()
            
            # Content Recognition Section
            print("\n🎵 Content Recognition")
            print_separator("-")
            print(f"Type: {'Music' if result.get('confidence', 0) > 50 else 'Speech/Other'}")
            
            if result.get('title'):
                print("\nTrack Information:")
                print(f"Title: {result['title']}")
                print(f"Artist: {result['artist']}")
                print(f"Album: {result.get('album', 'N/A')}")
                print(f"ISRC: {result.get('isrc', 'N/A')}")
                print(f"Detection Confidence: {result.get('confidence', 0)}%")
                print(f"Duration: {(datetime.now() - start_time).total_seconds():.2f}s")
                
                # External Services Links
                print("\n🔗 External Services:")
                if result.get('external_metadata', {}).get('spotify'):
                    spotify_data = result['external_metadata']['spotify']
                    print(f"Spotify: {spotify_data.get('external_urls', {}).get('spotify', 'N/A')}")
                    # Add more Spotify details if available
                    if isinstance(spotify_data, dict):
                        if 'album' in spotify_data:
                            print(f"Release Date: {spotify_data['album'].get('release_date', 'N/A')}")
                        if 'popularity' in spotify_data:
                            print(f"Popularity: {spotify_data.get('popularity', 'N/A')}/100")
                
                if result.get('external_metadata', {}).get('deezer'):
                    deezer_data = result['external_metadata']['deezer']
                    print(f"Deezer: {deezer_data.get('link', 'N/A')}")
                
                # Detection Metadata
                print("\n📝 Detection Details:")
                print(f"Timestamp: {result.get('detected_at')}")
                print(f"Sample Duration: {(datetime.now() - start_time).total_seconds():.2f}s")
            else:
                print("\nNo music detected in the sample")
                if "audio_features" in result:
                    print(f"Music Likelihood: {format_feature_value(features.get('music_likelihood', 0))}%")
        else:
            print("\n❌ Detection Error:")
            print(result.get('error', 'Unknown error occurred'))
            
        print_separator("=")
        
    except Exception as e:
        logger.error(f"Error in test_detection: {str(e)}", exc_info=True)
        print("\n❌ Error occurred:")
        print(str(e))
        print_separator("=")

if __name__ == "__main__":
    test_detection() 