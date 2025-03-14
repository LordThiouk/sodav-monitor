# Channels Router Module

This module handles all operations related to radio stations in the SODAV Monitor system.

## Structure

The channels router is divided into three main components:

1. **Core (`core.py`)**: Basic CRUD operations for radio stations
2. **Status (`status.py`)**: Station status management and history
3. **Monitoring (`monitoring.py`)**: Station monitoring and music detection

## Endpoints

### Core Endpoints

- `GET /api/channels`: Get a list of radio stations
- `POST /api/channels`: Create a new radio station
- `GET /api/channels/{station_id}`: Get a specific radio station
- `PUT /api/channels/{station_id}`: Update a specific radio station
- `DELETE /api/channels/{station_id}`: Delete a specific radio station

### Status Endpoints

- `GET /api/channels/{station_id}/status`: Get the current status of a station
- `PUT /api/channels/{station_id}/status`: Update the status of a station
- `GET /api/channels/status/summary`: Get a summary of station statuses
- `GET /api/channels/status/history/{station_id}`: Get the status history for a station

### Monitoring Endpoints

- `POST /api/channels/{station_id}/check`: Check the status of a station
- `POST /api/channels/refresh`: Refresh the status of all stations
- `POST /api/channels/{station_id}/detect-music`: Detect music playing on a station
- `GET /api/channels/{station_id}/detections`: Get music detections for a station
- `GET /api/channels/stats`: Get monitoring statistics for all stations

## Authentication

All endpoints require authentication. The user must be logged in and have a valid JWT token.

## Error Handling

All endpoints include proper error handling for common scenarios:

- 404 Not Found: When a station doesn't exist
- 400 Bad Request: When input validation fails
- 401 Unauthorized: When authentication fails

## Background Tasks

Several operations are performed in the background to avoid blocking the API:

- Station status checks
- Music detection

## Dependencies

This module depends on:

- `backend.models.database`: Database access
- `backend.models.models`: Data models
- `backend.utils.auth`: Authentication utilities
- `backend.utils.streams.stream_checker`: Stream status checking
- `backend.detection.music_detector`: Music detection

## Usage Example

```python
# Get a list of active stations
response = await client.get("/api/channels?status=ACTIVE", headers=auth_headers)
active_stations = response.json()

# Create a new station
new_station = {
    "name": "Test Station",
    "stream_url": "http://example.com/stream",
    "location": "Dakar"
}
response = await client.post("/api/channels", json=new_station, headers=auth_headers)
created_station = response.json()

# Check a station's status
response = await client.post(f"/api/channels/{station_id}/check", headers=auth_headers)

# Get music detections for a station
response = await client.get(f"/api/channels/{station_id}/detections", headers=auth_headers)
detections = response.json()
```
