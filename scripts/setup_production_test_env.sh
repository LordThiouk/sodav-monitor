#!/bin/bash

# SODAV Monitor Production-Like Test Environment Setup Script
# This script automates the setup of a production-like test environment for SODAV Monitor

# Exit on error
set -e

# Print colored messages
print_green() {
    echo -e "\e[32m$1\e[0m"
}

print_yellow() {
    echo -e "\e[33m$1\e[0m"
}

print_red() {
    echo -e "\e[31m$1\e[0m"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_yellow "This script requires sudo privileges for system package installation."
    print_yellow "Please enter your password when prompted."
    
    # Try to get sudo privileges
    sudo -v
    
    # Check if sudo was successful
    if [ $? -ne 0 ]; then
        print_red "Failed to obtain sudo privileges. Please run this script with sudo."
        exit 1
    fi
fi

# Welcome message
print_green "========================================================"
print_green "  SODAV Monitor Production-Like Test Environment Setup"
print_green "========================================================"
print_green "This script will set up a production-like test environment"
print_green "for SODAV Monitor, including all required dependencies for"
print_green "external detection services (AcoustID and AudD)."
print_green "========================================================"
echo ""

# Check OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    print_green "Detected Linux operating system."
    
    # Detect distribution
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
        print_green "Distribution: $OS $VER"
    else
        print_yellow "Could not determine Linux distribution. Assuming Debian/Ubuntu compatible."
        OS="Unknown"
    fi
    
    # Install system dependencies
    print_green "Installing system dependencies..."
    sudo apt update
    
    print_green "Installing audio processing libraries..."
    sudo apt install -y ffmpeg libavcodec-extra libsndfile1 portaudio19-dev
    
    print_green "Installing chromaprint for AcoustID fingerprinting..."
    sudo apt install -y libchromaprint-dev libchromaprint-tools
    
    print_green "Installing additional audio libraries..."
    sudo apt install -y libasound2-dev python3-dev python3-pip python3-venv
    
    print_green "Installing PostgreSQL..."
    sudo apt install -y postgresql postgresql-contrib
    
    print_green "Installing Redis..."
    sudo apt install -y redis-server
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    print_green "Detected macOS operating system."
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        print_yellow "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    print_green "Installing system dependencies with Homebrew..."
    brew update
    
    print_green "Installing audio processing libraries..."
    brew install ffmpeg
    
    print_green "Installing chromaprint for AcoustID fingerprinting..."
    brew install chromaprint
    
    print_green "Installing PostgreSQL..."
    brew install postgresql
    
    print_green "Installing Redis..."
    brew install redis
    
    # Start services
    print_green "Starting PostgreSQL service..."
    brew services start postgresql
    
    print_green "Starting Redis service..."
    brew services start redis
    
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    print_red "Windows detected. This script is optimized for Linux/macOS."
    print_yellow "For Windows, please follow the manual setup instructions in docs/tests/production_test_environment.md"
    print_yellow "or consider using Windows Subsystem for Linux (WSL) or Docker."
    exit 1
else
    print_red "Unsupported operating system: $OSTYPE"
    print_yellow "Please follow the manual setup instructions in docs/tests/production_test_environment.md"
    exit 1
fi

# Create Python virtual environment
print_green "Setting up Python virtual environment..."
python3 -m venv sodav-env

# Activate virtual environment
print_green "Activating virtual environment..."
source sodav-env/bin/activate

# Upgrade pip
print_green "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
print_green "Installing Python dependencies..."
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    print_yellow "requirements.txt not found. Skipping package installation."
    print_yellow "Please install required packages manually."
fi

# Install additional audio packages
print_green "Installing additional audio processing packages..."
pip install pyaudio soundfile librosa chromaprint acoustid pydub

# Set up PostgreSQL database
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    print_green "Setting up PostgreSQL database..."
    
    # Check if PostgreSQL service is running
    if systemctl is-active --quiet postgresql; then
        print_green "PostgreSQL service is running."
    else
        print_green "Starting PostgreSQL service..."
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    fi
    
    # Create database and user
    print_green "Creating database and user..."
    sudo -u postgres psql -c "CREATE USER sodav_test WITH PASSWORD 'sodav_test_password';" || print_yellow "User may already exist."
    sudo -u postgres psql -c "CREATE DATABASE sodav_test OWNER sodav_test;" || print_yellow "Database may already exist."
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sodav_test TO sodav_test;" || print_yellow "Privileges may already be granted."
    
    # Set up Redis
    print_green "Setting up Redis..."
    
    # Check if Redis service is running
    if systemctl is-active --quiet redis-server; then
        print_green "Redis service is running."
    else
        print_green "Starting Redis service..."
        sudo systemctl start redis-server
        sudo systemctl enable redis-server
    fi
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    print_green "Setting up PostgreSQL database..."
    
    # Create database and user
    print_green "Creating database and user..."
    createuser -s sodav_test || print_yellow "User may already exist."
    psql -c "ALTER USER sodav_test WITH PASSWORD 'sodav_test_password';" postgres || print_yellow "Could not set password."
    createdb -O sodav_test sodav_test || print_yellow "Database may already exist."
fi

# Create .env file
print_green "Creating .env file..."
cat > .env << EOF
# Database configuration
DATABASE_URL=postgresql://sodav_test:sodav_test_password@localhost/sodav_test

# Redis configuration
REDIS_URL=redis://localhost:6379/0

# External API keys
ACOUSTID_API_KEY=your_acoustid_api_key
AUDD_API_KEY=your_audd_api_key
MUSICBRAINZ_API_KEY=your_musicbrainz_api_key

# Logging configuration
LOG_LEVEL=INFO
EOF

print_yellow "Please edit the .env file and add your actual API keys."

# Create test script for external services
print_green "Creating test script for external services..."
cat > test_external_services.py << EOF
import acoustid
import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_acoustid():
    print("Testing AcoustID connection...")
    api_key = os.getenv("ACOUSTID_API_KEY")
    if not api_key or api_key == "your_acoustid_api_key":
        print("Error: ACOUSTID_API_KEY not found or not set in environment variables")
        return False
    
    try:
        # Simple API call to test connection
        result = acoustid.lookup(api_key, "4115aae1201a58d50aaf9577f5086530")
        print("AcoustID connection successful")
        return True
    except Exception as e:
        print(f"AcoustID connection failed: {str(e)}")
        return False

def test_audd():
    print("Testing AudD connection...")
    api_key = os.getenv("AUDD_API_KEY")
    if not api_key or api_key == "your_audd_api_key":
        print("Error: AUDD_API_KEY not found or not set in environment variables")
        return False
    
    try:
        # Simple API call to test connection
        url = f"https://api.audd.io/getApiStatus/?api_token={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            print("AudD connection successful")
            return True
        else:
            print(f"AudD connection failed with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"AudD connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    acoustid_success = test_acoustid()
    audd_success = test_audd()
    
    if acoustid_success and audd_success:
        print("All external services are configured correctly!")
    else:
        print("Some external services are not configured correctly. Please check the logs above.")
EOF

# Create test data script
print_green "Creating test data script..."
cat > generate_test_data.py << EOF
from backend.models.models import Base, RadioStation, Track, Artist, Label
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Create test radio stations
stations = [
    {"name": "RTS Radio Sénégal", "url": "https://stream.zeno.fm/eyuiqh60p1qtv", "country": "Senegal", "region": "Dakar"},
    {"name": "Zik FM", "url": "https://stream.zeno.fm/yd4b9ub4qzzuv", "country": "Senegal", "region": "Dakar"},
    {"name": "RFM Sénégal", "url": "https://stream.zeno.fm/a83m5qyp1wzuv", "country": "Senegal", "region": "Dakar"},
    {"name": "Sud FM", "url": "https://stream.zeno.fm/hhq0eny4qzzuv", "country": "Senegal", "region": "Dakar"},
    {"name": "Afia FM", "url": "https://stream.zeno.fm/kstz6p2cn2zuv", "country": "Senegal", "region": "Dakar"}
]

# Create test artists
artists = [
    {"name": "Youssou N'Dour", "country": "Senegal"},
    {"name": "Baaba Maal", "country": "Senegal"},
    {"name": "Orchestra Baobab", "country": "Senegal"},
    {"name": "Cheikh Lô", "country": "Senegal"},
    {"name": "Ismael Lô", "country": "Senegal"}
]

# Create test labels
labels = [
    {"name": "Jololi", "country": "Senegal"},
    {"name": "Syllart Records", "country": "Senegal"},
    {"name": "Prince Arts", "country": "Senegal"},
    {"name": "Studio Bogolan", "country": "Mali"},
    {"name": "World Circuit", "country": "UK"}
]

# Create test tracks
tracks = [
    {"title": "7 Seconds", "isrc": "GBDUW0000059", "artist_id": 1, "label_id": 1},
    {"title": "Birima", "isrc": "GBDUW0000060", "artist_id": 1, "label_id": 1},
    {"title": "Set", "isrc": "GBDUW0000061", "artist_id": 2, "label_id": 2},
    {"title": "Utru Horas", "isrc": "GBDUW0000062", "artist_id": 3, "label_id": 5},
    {"title": "Bamba", "isrc": "GBDUW0000063", "artist_id": 4, "label_id": 3}
]

def create_test_data():
    # Add stations
    for station_data in stations:
        station = RadioStation(**station_data)
        session.add(station)
    
    # Add artists
    for artist_data in artists:
        artist = Artist(**artist_data)
        session.add(artist)
    
    # Add labels
    for label_data in labels:
        label = Label(**label_data)
        session.add(label)
    
    # Commit to get IDs
    session.commit()
    
    # Add tracks
    for track_data in tracks:
        track = Track(**track_data)
        session.add(track)
    
    # Final commit
    session.commit()
    print("Test data created successfully!")

if __name__ == "__main__":
    create_test_data()
EOF

# Create test directory for audio samples
print_green "Creating test directory for audio samples..."
mkdir -p test_audio_samples

# Create directory for test results
print_green "Creating directory for test results..."
mkdir -p test_results

# Verify installations
print_green "Verifying installations..."

# Check ffmpeg
if command -v ffmpeg &> /dev/null; then
    print_green "ffmpeg is installed: $(ffmpeg -version | head -n 1)"
else
    print_red "ffmpeg is not installed or not in PATH."
fi

# Check chromaprint
if command -v fpcalc &> /dev/null; then
    print_green "chromaprint is installed: $(fpcalc -version)"
else
    print_red "chromaprint (fpcalc) is not installed or not in PATH."
fi

# Final instructions
print_green "========================================================"
print_green "  Setup Complete!"
print_green "========================================================"
print_green "Next steps:"
print_green "1. Edit the .env file and add your actual API keys"
print_green "2. Run database migrations: python -m alembic upgrade head"
print_green "3. Generate test data: python generate_test_data.py"
print_green "4. Test external services: python test_external_services.py"
print_green "5. Run the end-to-end tests: python -m pytest backend/tests/integration/test_end_to_end.py -v"
print_green "========================================================"
print_green "For more information, see docs/tests/production_test_environment.md"
print_green "========================================================" 