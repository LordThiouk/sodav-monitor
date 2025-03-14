# SODAV Monitor Production-Like Test Environment Setup Script for Windows
# This script automates the setup of a production-like test environment for SODAV Monitor on Windows

# Function to print colored messages
function Write-ColorOutput {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,

        [Parameter(Mandatory=$false)]
        [string]$ForegroundColor = "White"
    )

    $originalColor = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    Write-Output $Message
    $host.UI.RawUI.ForegroundColor = $originalColor
}

# Welcome message
Write-ColorOutput "========================================================" "Green"
Write-ColorOutput "  SODAV Monitor Production-Like Test Environment Setup" "Green"
Write-ColorOutput "========================================================" "Green"
Write-ColorOutput "This script will set up a production-like test environment" "Green"
Write-ColorOutput "for SODAV Monitor, including all required dependencies for" "Green"
Write-ColorOutput "external detection services (AcoustID and AudD)." "Green"
Write-ColorOutput "========================================================" "Green"
Write-Output ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-ColorOutput "This script requires administrator privileges. Please run PowerShell as administrator." "Yellow"
    exit
}

# Check if Chocolatey is installed
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-ColorOutput "Chocolatey is not installed. Installing Chocolatey..." "Yellow"
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# Install system dependencies
Write-ColorOutput "Installing system dependencies..." "Green"

# Install Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-ColorOutput "Installing Python..." "Green"
    choco install python -y

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}
else {
    Write-ColorOutput "Python is already installed: $(python --version)" "Green"
}

# Install FFmpeg
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-ColorOutput "Installing FFmpeg..." "Green"
    choco install ffmpeg -y

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}
else {
    Write-ColorOutput "FFmpeg is already installed: $(ffmpeg -version | Select-Object -First 1)" "Green"
}

# Install PostgreSQL
if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    Write-ColorOutput "Installing PostgreSQL..." "Green"
    choco install postgresql -y

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}
else {
    Write-ColorOutput "PostgreSQL is already installed: $(psql --version)" "Green"
}

# Install Redis
if (-not (Get-Command redis-server -ErrorAction SilentlyContinue)) {
    Write-ColorOutput "Installing Redis..." "Green"
    choco install redis-server -y

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}
else {
    Write-ColorOutput "Redis is already installed" "Green"
}

# Install Chromaprint (fpcalc)
$fpcalcPath = "C:\Program Files (x86)\Chromaprint\fpcalc.exe"
if (-not (Test-Path $fpcalcPath)) {
    Write-ColorOutput "Installing Chromaprint (fpcalc)..." "Green"

    # Create temporary directory
    $tempDir = [System.IO.Path]::GetTempPath() + [System.Guid]::NewGuid().ToString()
    New-Item -ItemType Directory -Path $tempDir | Out-Null

    # Download Chromaprint
    $chromaprintUrl = "https://github.com/acoustid/chromaprint/releases/download/v1.5.1/chromaprint-fpcalc-1.5.1-windows-x86_64.zip"
    $chromaprintZip = "$tempDir\chromaprint.zip"
    Invoke-WebRequest -Uri $chromaprintUrl -OutFile $chromaprintZip

    # Extract Chromaprint
    Expand-Archive -Path $chromaprintZip -DestinationPath $tempDir

    # Create installation directory
    $installDir = "C:\Program Files (x86)\Chromaprint"
    if (-not (Test-Path $installDir)) {
        New-Item -ItemType Directory -Path $installDir | Out-Null
    }

    # Copy fpcalc.exe to installation directory
    Copy-Item -Path "$tempDir\chromaprint-fpcalc-1.5.1-windows-x86_64\fpcalc.exe" -Destination $installDir

    # Add to PATH
    $currentPath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    if (-not $currentPath.Contains($installDir)) {
        [System.Environment]::SetEnvironmentVariable("Path", $currentPath + ";" + $installDir, "Machine")
    }

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

    # Clean up
    Remove-Item -Path $tempDir -Recurse -Force
}
else {
    Write-ColorOutput "Chromaprint (fpcalc) is already installed" "Green"
}

# Create Python virtual environment
Write-ColorOutput "Setting up Python virtual environment..." "Green"
if (-not (Test-Path "sodav-env")) {
    python -m venv sodav-env
}
else {
    Write-ColorOutput "Virtual environment already exists" "Green"
}

# Activate virtual environment
Write-ColorOutput "Activating virtual environment..." "Green"
& .\sodav-env\Scripts\Activate.ps1

# Upgrade pip
Write-ColorOutput "Upgrading pip..." "Green"
python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies
Write-ColorOutput "Installing Python dependencies..." "Green"
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
}
else {
    Write-ColorOutput "requirements.txt not found. Skipping package installation." "Yellow"
    Write-ColorOutput "Please install required packages manually." "Yellow"
}

# Install additional audio packages
Write-ColorOutput "Installing additional audio processing packages..." "Green"
pip install pyaudio soundfile librosa pydub requests

# Install acoustid
Write-ColorOutput "Installing acoustid package..." "Green"
pip install pyacoustid

# Set up PostgreSQL database
Write-ColorOutput "Setting up PostgreSQL database..." "Green"

# Start PostgreSQL service
Write-ColorOutput "Starting PostgreSQL service..." "Green"
Start-Service postgresql

# Create database and user
Write-ColorOutput "Creating database and user..." "Green"
$pgPassword = "sodav_test_password"

# Create a temporary SQL file
$sqlFile = [System.IO.Path]::GetTempFileName()
@"
CREATE USER sodav_test WITH PASSWORD '$pgPassword';
CREATE DATABASE sodav_test OWNER sodav_test;
GRANT ALL PRIVILEGES ON DATABASE sodav_test TO sodav_test;
"@ | Out-File -FilePath $sqlFile -Encoding ASCII

# Run the SQL commands
$env:PGPASSWORD = "postgres"
psql -U postgres -f $sqlFile

# Clean up
Remove-Item -Path $sqlFile

# Start Redis service
Write-ColorOutput "Starting Redis service..." "Green"
Start-Service redis

# Create .env file
Write-ColorOutput "Creating .env file..." "Green"
@"
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
"@ | Out-File -FilePath ".env" -Encoding ASCII

Write-ColorOutput "Please edit the .env file and add your actual API keys." "Yellow"

# Create test script for external services
Write-ColorOutput "Creating test script for external services..." "Green"
@"
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
"@ | Out-File -FilePath "test_external_services.py" -Encoding ASCII

# Create test data script
Write-ColorOutput "Creating test data script..." "Green"
@"
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
"@ | Out-File -FilePath "generate_test_data.py" -Encoding ASCII

# Create test directory for audio samples
Write-ColorOutput "Creating test directory for audio samples..." "Green"
if (-not (Test-Path "test_audio_samples")) {
    New-Item -ItemType Directory -Path "test_audio_samples" | Out-Null
}

# Create directory for test results
Write-ColorOutput "Creating directory for test results..." "Green"
if (-not (Test-Path "test_results")) {
    New-Item -ItemType Directory -Path "test_results" | Out-Null
}

# Verify installations
Write-ColorOutput "Verifying installations..." "Green"

# Check ffmpeg
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-ColorOutput "ffmpeg is installed: $(ffmpeg -version | Select-Object -First 1)" "Green"
}
else {
    Write-ColorOutput "ffmpeg is not installed or not in PATH." "Red"
}

# Check chromaprint
if (Test-Path $fpcalcPath) {
    Write-ColorOutput "chromaprint (fpcalc) is installed" "Green"
}
else {
    Write-ColorOutput "chromaprint (fpcalc) is not installed or not in PATH." "Red"
}

# Final instructions
Write-ColorOutput "========================================================" "Green"
Write-ColorOutput "  Setup Complete!" "Green"
Write-ColorOutput "========================================================" "Green"
Write-ColorOutput "Next steps:" "Green"
Write-ColorOutput "1. Edit the .env file and add your actual API keys" "Green"
Write-ColorOutput "2. Run database migrations: python -m alembic upgrade head" "Green"
Write-ColorOutput "3. Generate test data: python generate_test_data.py" "Green"
Write-ColorOutput "4. Test external services: python test_external_services.py" "Green"
Write-ColorOutput "5. Run the end-to-end tests: python -m pytest backend/tests/integration/test_end_to_end.py -v" "Green"
Write-ColorOutput "========================================================" "Green"
Write-ColorOutput "For more information, see docs/tests/production_test_environment.md" "Green"
Write-ColorOutput "========================================================" "Green"
