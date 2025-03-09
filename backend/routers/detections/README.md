# Detections Router Module

This module handles all operations related to music detection in the SODAV Monitor system.

## Structure

The detections router is divided into three main components:

1. **Core (`core.py`)**: Basic CRUD operations for detections
2. **Search (`search.py`)**: Search and filtering operations for detections
3. **Processing (`processing.py`)**: Audio processing and music detection operations

## Endpoints

### Core Endpoints

- `GET /api/detections`: Get a list of detections with optional filtering
- `POST /api/detections`: Create a new detection
- `GET /api/detections/{detection_id}`: Get a specific detection
- `DELETE /api/detections/{detection_id}`: Delete a specific detection

### Search Endpoints

- `GET /api/detections/search`: Search for detections by track title, artist name, or station name
- `GET /api/detections/station/{station_id}`: Get detections for a specific radio station
- `GET /api/detections/track/{track_id}`: Get detections for a specific track
- `GET /api/detections/latest`: Get the latest detections across all stations

### Processing Endpoints

- `POST /api/detections/process`: Process an audio file to detect music
- `POST /api/detections/detect-music`: Detect music on a specific radio station
- `POST /api/detections/detect-music-all`: Detect music on all active radio stations

## Authentication

All endpoints require authentication. The user must be logged in and have a valid JWT token.

## Error Handling

All endpoints include proper error handling for common scenarios:

- 404 Not Found: When a detection, station, or track doesn't exist
- 400 Bad Request: When input validation fails
- 401 Unauthorized: When authentication fails
- 500 Internal Server Error: When audio processing fails

## Background Tasks

Several operations are performed in the background to avoid blocking the API:

- Audio processing
- Music detection on stations

## Dependencies

This module depends on:

- `backend.models.database`: Database access
- `backend.models.models`: Data models
- `backend.utils.auth`: Authentication utilities
- `backend.detection.audio_processor.core`: Audio processing
- `backend.detection.music_detector`: Music detection

## Usage Example

```python
# Get a list of detections
response = await client.get("/api/detections", headers=auth_headers)
detections = response.json()

# Search for detections
response = await client.get("/api/detections/search?query=Test", headers=auth_headers)
search_results = response.json()

# Process an audio file
with open("test.mp3", "rb") as f:
    files = {"file": ("test.mp3", f, "audio/mpeg")}
    response = await client.post("/api/detections/process", files=files, headers=auth_headers)
    process_result = response.json()

# Detect music on a station
response = await client.post(f"/api/detections/detect-music?station_id=1", headers=auth_headers)
detection_result = response.json()

# Detect music on all active stations
response = await client.post("/api/detections/detect-music-all", headers=auth_headers)
all_stations_result = response.json()
``` 