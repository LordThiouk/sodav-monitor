# Setting Up a Production-Like Test Environment for SODAV Monitor

This guide provides detailed instructions for setting up a production-like environment to fully test the SODAV Monitor system, including external detection services (AcoustID and AudD) that require specialized audio conversion capabilities.

## Overview

The standard test environment has limitations, particularly with external detection services that require specific audio conversion libraries. This guide helps you create an environment that closely mimics production, allowing for comprehensive testing of all system components.

## Prerequisites

- Linux-based system (Ubuntu 20.04 or later recommended)
- Python 3.8 or later
- Docker and Docker Compose (optional, for containerized setup)
- Administrator/sudo access
- Internet connection for accessing radio streams and external APIs

## Step 1: System Dependencies

Install the required system libraries for audio processing:

```bash
# Update package lists
sudo apt update

# Install audio processing libraries
sudo apt install -y ffmpeg libavcodec-extra libsndfile1 portaudio19-dev

# Install chromaprint for AcoustID fingerprinting
sudo apt install -y libchromaprint-dev libchromaprint-tools

# Install additional audio libraries
sudo apt install -y libasound2-dev python3-dev python3-pip python3-venv
```

## Step 2: Python Environment Setup

Create and configure a dedicated Python virtual environment:

```bash
# Create a virtual environment
python3 -m venv sodav-env

# Activate the environment
source sodav-env/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install required Python packages
pip install -r requirements.txt

# Install additional audio processing packages
pip install pyaudio soundfile librosa chromaprint acoustid pydub
```

## Step 3: Database Setup

Set up a PostgreSQL database for testing:

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create a database and user for testing
sudo -u postgres psql -c "CREATE USER sodav_test WITH PASSWORD 'sodav_test_password';"
sudo -u postgres psql -c "CREATE DATABASE sodav_test OWNER sodav_test;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sodav_test TO sodav_test;"
```

## Step 4: Redis Setup

Install and configure Redis for caching:

```bash
# Install Redis
sudo apt install -y redis-server

# Configure Redis to start on boot
sudo systemctl enable redis-server

# Start Redis
sudo systemctl start redis-server
```

## Step 5: API Keys Configuration

Configure the necessary API keys for external services:

```bash
# Create a .env file in the project root
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
```

Replace `your_acoustid_api_key`, `your_audd_api_key`, and `your_musicbrainz_api_key` with your actual API keys.

### Obtaining API Keys

1. **AcoustID API Key**:
   - Register at [https://acoustid.org/login/register](https://acoustid.org/login/register)
   - After registration, request an API key at [https://acoustid.org/api-key](https://acoustid.org/api-key)

2. **AudD API Key**:
   - Sign up at [https://dashboard.audd.io/](https://dashboard.audd.io/)
   - Your API key will be available in your dashboard

3. **MusicBrainz API Key**:
   - While MusicBrainz doesn't require an API key, you should register your application
   - Follow the guidelines at [https://musicbrainz.org/doc/MusicBrainz_API](https://musicbrainz.org/doc/MusicBrainz_API)

## Step 6: Audio Conversion Setup

Ensure proper audio conversion capabilities:

```bash
# Test ffmpeg installation
ffmpeg -version

# Test chromaprint installation
fpcalc -version

# Create a test directory for audio samples
mkdir -p test_audio_samples
```

## Step 7: Verify External Service Integration

Test the connection to external services:

```bash
# Create a simple test script
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
    if not api_key:
        print("Error: ACOUSTID_API_KEY not found in environment variables")
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
    if not api_key:
        print("Error: AUDD_API_KEY not found in environment variables")
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

# Run the test script
python test_external_services.py
```

## Step 8: Database Migration

Initialize and migrate the database:

```bash
# Run database migrations
python -m alembic upgrade head
```

## Step 9: Test Data Setup

Prepare test data for comprehensive testing:

```bash
# Create a script to generate test data
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

# Run the script to generate test data
python generate_test_data.py
```

## Step 10: Running End-to-End Tests

Now you can run the end-to-end tests with full functionality:

```bash
# Run all E2E tests
python -m pytest backend/tests/integration/test_end_to_end.py -v

# Run a specific test
python -m pytest backend/tests/integration/test_end_to_end.py::TestEndToEnd::test_detection_workflow -v

# Run with log output
python -m pytest backend/tests/integration/test_end_to_end.py -v --log-cli-level=INFO
```

## Step 11: Monitoring Test Results

Set up monitoring to track test results:

```bash
# Create a directory for test results
mkdir -p test_results

# Run tests with JUnit XML output
python -m pytest backend/tests/integration/test_end_to_end.py -v --junitxml=test_results/e2e_test_results.xml

# Generate HTML report (requires pytest-html)
pip install pytest-html
python -m pytest backend/tests/integration/test_end_to_end.py -v --html=test_results/e2e_test_report.html
```

## Step 12: Containerized Setup (Optional)

For a fully isolated environment, you can use Docker:

```bash
# Create a Dockerfile
cat > Dockerfile << EOF
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    ffmpeg \\
    libavcodec-extra \\
    libsndfile1 \\
    portaudio19-dev \\
    libchromaprint-dev \\
    libchromaprint-tools \\
    libasound2-dev \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional audio packages
RUN pip install --no-cache-dir pyaudio soundfile librosa chromaprint acoustid pydub

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app

# Command to run tests
CMD ["python", "-m", "pytest", "backend/tests/integration/test_end_to_end.py", "-v", "--log-cli-level=INFO"]
EOF

# Create docker-compose.yml
cat > docker-compose.yml << EOF
version: '3.8'

services:
  db:
    image: postgres:13
    environment:
      POSTGRES_USER: sodav_test
      POSTGRES_PASSWORD: sodav_test_password
      POSTGRES_DB: sodav_test
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6
    ports:
      - "6379:6379"

  app:
    build: .
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://sodav_test:sodav_test_password@db/sodav_test
      - REDIS_URL=redis://redis:6379/0
      - ACOUSTID_API_KEY=${ACOUSTID_API_KEY}
      - AUDD_API_KEY=${AUDD_API_KEY}
      - MUSICBRAINZ_API_KEY=${MUSICBRAINZ_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - .:/app

volumes:
  postgres_data:
EOF

# Build and run with Docker Compose
docker-compose up --build
```

## Troubleshooting

### Common Issues and Solutions

1. **Audio Conversion Failures**:
   - Ensure ffmpeg is properly installed: `ffmpeg -version`
   - Check that libsndfile is installed: `ldconfig -p | grep libsndfile`
   - Verify chromaprint installation: `fpcalc -version`

2. **API Key Issues**:
   - Verify API keys are correctly set in the .env file
   - Check API key validity by running the test_external_services.py script
   - Ensure you haven't exceeded API rate limits

3. **Database Connection Issues**:
   - Verify PostgreSQL is running: `sudo systemctl status postgresql`
   - Check connection parameters in the .env file
   - Ensure the database user has proper permissions

4. **Redis Connection Issues**:
   - Verify Redis is running: `sudo systemctl status redis-server`
   - Check Redis connection string in the .env file

5. **Python Package Issues**:
   - Ensure all dependencies are installed: `pip list`
   - Try reinstalling problematic packages: `pip uninstall package_name && pip install package_name`

### Logs and Debugging

For detailed debugging:

```bash
# Run tests with maximum verbosity
python -m pytest backend/tests/integration/test_end_to_end.py -vv --log-cli-level=DEBUG

# Check system logs for audio processing issues
sudo journalctl | grep -E 'ffmpeg|audio|chromaprint'

# Check Python package versions
pip freeze > installed_packages.txt
cat installed_packages.txt
```

## Conclusion

This production-like environment allows you to fully test all aspects of the SODAV Monitor system, including the external detection services that require specialized audio conversion capabilities. By following these steps, you can ensure that your tests accurately reflect how the system will behave in production.

Remember to keep your API keys secure and never commit them to version control. Use environment variables or secure vaults for production deployments.

## Next Steps

After setting up this environment, consider:

1. Creating automated CI/CD pipelines that use this environment
2. Developing benchmark tests to measure system performance
3. Setting up monitoring for the production environment
4. Creating a staging environment that mirrors this setup
