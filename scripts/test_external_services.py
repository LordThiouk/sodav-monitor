#!/usr/bin/env python3
"""
Test script for external services used by SODAV Monitor.

This script tests the connection to AcoustID and AudD services to verify
that the API keys are valid and the services are accessible.
"""

import json
import logging
import os
import sys

import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("external_services_test")

# Load environment variables from .env file
load_dotenv()


def test_acoustid():
    """Test connection to AcoustID service."""
    logger.info("Testing AcoustID connection...")
    api_key = os.getenv("ACOUSTID_API_KEY")

    if not api_key or api_key == "your_acoustid_api_key":
        logger.error("ACOUSTID_API_KEY not found or not set in environment variables")
        return False

    try:
        # Import acoustid here to avoid import errors if not installed
        try:
            import acoustid
        except ImportError:
            logger.error("acoustid package not installed. Install with: pip install pyacoustid")
            return False

        # Simple API call to test connection
        # Using a known fingerprint for testing
        result = acoustid.lookup(api_key, "4115aae1201a58d50aaf9577f5086530")

        if result:
            logger.info("AcoustID connection successful")
            logger.info(f"Response: {result}")
            return True
        else:
            logger.error("AcoustID returned empty result")
            return False

    except Exception as e:
        logger.error(f"AcoustID connection failed: {str(e)}")
        return False


def test_audd():
    """Test connection to AudD service."""
    logger.info("Testing AudD connection...")
    api_key = os.getenv("AUDD_API_KEY")

    if not api_key or api_key == "your_audd_api_key":
        logger.error("AUDD_API_KEY not found or not set in environment variables")
        return False

    try:
        # Simple API call to test connection
        url = f"https://api.audd.io/getApiStatus/?api_token={api_key}"
        response = requests.get(url)

        if response.status_code == 200:
            response_json = response.json()
            logger.info("AudD connection successful")
            logger.info(f"Response: {json.dumps(response_json, indent=2)}")
            return True
        else:
            logger.error(f"AudD connection failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False

    except Exception as e:
        logger.error(f"AudD connection failed: {str(e)}")
        return False


def test_ffmpeg():
    """Test if ffmpeg is installed and working."""
    logger.info("Testing ffmpeg installation...")

    try:
        import subprocess

        result = subprocess.run(
            ["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        if result.returncode == 0:
            logger.info("ffmpeg is installed and working")
            logger.info(f"Version: {result.stdout.splitlines()[0]}")
            return True
        else:
            logger.error("ffmpeg test failed")
            logger.error(f"Error: {result.stderr}")
            return False

    except FileNotFoundError:
        logger.error("ffmpeg not found. Please install ffmpeg.")
        return False
    except Exception as e:
        logger.error(f"Error testing ffmpeg: {str(e)}")
        return False


def test_chromaprint():
    """Test if chromaprint (fpcalc) is installed and working."""
    logger.info("Testing chromaprint (fpcalc) installation...")

    try:
        import subprocess

        result = subprocess.run(
            ["fpcalc", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        if result.returncode == 0:
            logger.info("chromaprint (fpcalc) is installed and working")
            logger.info(f"Version: {result.stdout.strip()}")
            return True
        else:
            logger.error("chromaprint (fpcalc) test failed")
            logger.error(f"Error: {result.stderr}")
            return False

    except FileNotFoundError:
        logger.error("chromaprint (fpcalc) not found. Please install chromaprint.")
        return False
    except Exception as e:
        logger.error(f"Error testing chromaprint: {str(e)}")
        return False


def test_audio_conversion():
    """Test audio conversion capabilities."""
    logger.info("Testing audio conversion capabilities...")

    try:
        import io

        import numpy as np
        import soundfile as sf

        # Generate a simple sine wave
        sample_rate = 44100
        duration = 1  # seconds
        frequency = 440  # Hz (A4)
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        audio_data = 0.5 * np.sin(2 * np.pi * frequency * t)

        # Convert to bytes
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format="WAV")
        buffer.seek(0)
        audio_bytes = buffer.read()

        # Try to read it back
        buffer = io.BytesIO(audio_bytes)
        data, sr = sf.read(buffer)

        if len(data) > 0 and sr == sample_rate:
            logger.info("Audio conversion test passed")
            return True
        else:
            logger.error("Audio conversion test failed")
            return False

    except ImportError as e:
        logger.error(f"Missing package for audio conversion: {str(e)}")
        logger.error("Install required packages with: pip install numpy soundfile")
        return False
    except Exception as e:
        logger.error(f"Error testing audio conversion: {str(e)}")
        return False


def main():
    """Run all tests and report results."""
    print("=" * 60)
    print("SODAV Monitor External Services Test")
    print("=" * 60)

    # Test system dependencies
    ffmpeg_success = test_ffmpeg()
    chromaprint_success = test_chromaprint()
    audio_conversion_success = test_audio_conversion()

    # Test external services
    acoustid_success = test_acoustid()
    audd_success = test_audd()

    # Print summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print(f"ffmpeg:           {'✅ PASSED' if ffmpeg_success else '❌ FAILED'}")
    print(f"chromaprint:      {'✅ PASSED' if chromaprint_success else '❌ FAILED'}")
    print(f"Audio Conversion: {'✅ PASSED' if audio_conversion_success else '❌ FAILED'}")
    print(f"AcoustID:         {'✅ PASSED' if acoustid_success else '❌ FAILED'}")
    print(f"AudD:             {'✅ PASSED' if audd_success else '❌ FAILED'}")
    print("=" * 60)

    # Overall result
    system_deps = ffmpeg_success and chromaprint_success and audio_conversion_success
    external_services = acoustid_success and audd_success

    if system_deps and external_services:
        print("✅ All tests passed! Your environment is correctly set up.")
        return 0
    elif system_deps and not external_services:
        print(
            "⚠️  System dependencies are correctly installed, but external services are not configured correctly."
        )
        print("   Please check your API keys and internet connection.")
        return 1
    elif not system_deps:
        print("❌ System dependencies are not correctly installed.")
        print(
            "   Please follow the setup instructions in docs/tests/production_test_environment.md"
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
