# Integration Testing Strategy

## Overview

This document outlines the integration testing strategy for the SODAV Monitor project. Integration tests verify that different components of the system work together correctly, ensuring that the system functions as expected in real-world scenarios.

## Goals

The goals of integration testing are to:

1. Verify that components interact correctly with each other
2. Identify issues that may not be caught by unit tests
3. Ensure that the system meets its requirements
4. Validate the system's behavior in real-world scenarios

## Integration Test Structure

Integration tests are organized by component:

```
backend/tests/integration/
├── api/                     # API integration tests
│   └── test_api_integration.py
├── detection/               # Detection system integration tests
│   ├── test_detection_integration.py
│   └── test_track_manager_system.py  # Track Manager system integration tests
├── analytics/               # Analytics system integration tests
│   └── test_analytics_integration.py
├── conftest.py              # Shared fixtures for integration tests
└── README.md                # Documentation for integration tests
```

Additionally, component-level integration tests are located in their respective module directories:

```
backend/tests/detection/audio_processor/
├── test_track_manager_integration.py  # Track Manager component integration tests
└── ...
```

## Test Fixtures

Integration tests use fixtures defined in `conftest.py` to set up the test environment. These fixtures include:

- `db_session`: A database session for the tests
- `test_user`: A test user for authentication
- `auth_headers`: Authentication headers for API requests
- `test_client`: A test client for making API requests

## Test Data

Integration tests create test data in the database as needed. This data is cleaned up after the tests are run to avoid polluting the database.

## Track Manager Integration Tests

The Track Manager has been refactored into multiple specialized components, requiring comprehensive integration testing to ensure these components work together correctly.

### Integration Testing Approach

The Track Manager integration tests are organized into two levels:

1. **Component Integration Tests**: Verify interactions between the different classes of the Track Manager
2. **System Integration Tests**: Verify interactions of the Track Manager with the database and other system components

### Component Integration Tests

Component integration tests are located in `backend/tests/detection/audio_processor/test_track_manager_integration.py` and focus on verifying that the different classes of the Track Manager interact correctly with each other. These tests use mocks to isolate the tests from external dependencies like the database.

Key test cases include:

- **test_track_creation_integration**: Verifies the integration between TrackManager and TrackCreator for track creation
- **test_local_detection_integration**: Verifies the integration between TrackManager and TrackFinder for local detection
- **test_isrc_detection_integration**: Verifies the integration for ISRC-based detection
- **test_external_detection_integration**: Verifies the integration with external detection services
- **test_fingerprint_integration**: Verifies the integration with the fingerprint handler
- **test_stats_recording_integration**: Verifies the integration with the statistics recorder
- **test_full_detection_pipeline_integration**: Verifies the complete detection pipeline

#### Example Component Integration Test

```python
@pytest.mark.asyncio
async def test_local_detection_integration(mock_db_session, mock_track, mock_features):
    """
    Test the integration between TrackManager and TrackFinder for local detection.

    This test verifies that the TrackManager correctly delegates to TrackFinder
    for local track detection and then to StatsRecorder for recording the detection.
    """
    # Configure the mocks
    track_finder = MagicMock(spec=TrackFinder)
    track_finder.find_local_match = AsyncMock(return_value={
        "track": {
            "id": 1,
            "title": "Test Track",
            "artist": "Test Artist"
        },
        "confidence": 0.9,
        "method": "local"
    })

    # ... other mocks ...

    # Create the TrackManager with mocked components
    track_manager = TrackManager(db_session=mock_db_session)

    # Call the method under test
    result = await track_manager.process_track(mock_features, station_id=1)

    # Verify the correct methods were called
    track_finder.find_local_match.assert_called_once_with(mock_features)
    stats_recorder.record_detection.assert_called_once()

    # Verify the result
    assert result["success"] is True
    assert result["track_id"] == 1
```

### System Integration Tests

System integration tests are located in `backend/tests/integration/detection/test_track_manager_system.py` and focus on verifying that the Track Manager works correctly with real database interactions and other system components. These tests use real database sessions and only mock external services like AcoustID and AudD.

Key test cases include:

- **test_local_detection_system**: Tests local detection with real database interactions
- **test_isrc_detection_system**: Tests ISRC-based detection with real database interactions
- **test_external_detection_system**: Tests external detection with real database interactions
- **test_stats_update_system**: Tests that statistics are updated correctly after detection
- **test_full_detection_pipeline_system**: Tests the complete detection pipeline with real components

#### Example System Integration Test

```python
@pytest.mark.asyncio
async def test_isrc_detection_system(self, db_session: Session, test_station: RadioStation,
                                    test_track: Track, test_features: dict):
    """
    Test the ISRC-based detection with real database interactions.

    This test:
    1. Creates a real track with ISRC in the database
    2. Configures the TrackManager to find this track by ISRC
    3. Verifies that the detection is properly recorded
    """
    # Create a TrackManager instance
    track_manager = TrackManager(db_session)

    # Add the ISRC to the features
    features = test_features.copy()
    features["isrc"] = test_track.isrc

    # Mock the find_local_match to fail
    with patch('backend.detection.audio_processor.track_manager.track_finder.TrackFinder.find_local_match',
              new_callable=AsyncMock) as mock_find_local:
        mock_find_local.return_value = None

        # Process the track
        result = await track_manager.process_track(features, station_id=test_station.id)

        # Verify the result
        assert result["success"] is True
        assert "track_id" in result
        assert "detection_id" in result

        # Verify the detection was recorded in the database
        detection = db_session.query(TrackDetection).filter(
            TrackDetection.id == result["detection_id"]
        ).first()

        assert detection is not None
        assert detection.track_id == test_track.id
        assert detection.station_id == test_station.id
        assert detection.method == "isrc"
```

### Running Track Manager Integration Tests

To run the component integration tests:

```bash
cd backend
python -m pytest tests/detection/audio_processor/test_track_manager_integration.py -v
```

To run the system integration tests:

```bash
cd backend
python -m pytest tests/integration/detection/test_track_manager_system.py -v
```

To run all Track Manager integration tests:

```bash
cd backend
python -m pytest tests/detection/audio_processor/test_track_manager_integration.py tests/integration/detection/test_track_manager_system.py -v
```

### Troubleshooting Track Manager Integration Tests

Common issues with Track Manager integration tests include:

1. **Mocking Issues**: Ensure that all necessary methods are properly mocked and return appropriate values
2. **Database Connection Issues**: Verify that the database session is properly configured
3. **Asynchronous Test Issues**: Make sure all async tests are properly decorated with `@pytest.mark.asyncio`
4. **Component Initialization**: Ensure that the TrackManager is initialized correctly with the appropriate dependencies

If tests are failing, check the logs for specific error messages and verify that the test environment is properly set up.

## Model and Schema Considerations

### Report Model

When testing the Report functionality, be aware of the differences between the database model and the API schema:

**Database Model (`Report` class):**
- Required fields: `title`, `type`, `report_type`, `format`, `status`
- Optional fields: `progress`, `completed_at`, `parameters`, `user_id`, `file_path`, `created_by`
- Auto-populated fields: `id`, `created_at`, `updated_at`

**API Schema (`ReportResponse` class):**
- Required fields: `id`, `title`, `type`, `format`, `status`, `created_at`, `updated_at`
- Required fields that come from parameters: `period_start`, `period_end`
- Optional fields: `file_path`, `error_message`, `filters`

When creating a test Report, include `period_start` and `period_end` in the `parameters` JSON field:

```python
report = Report(
    title="Test Report",
    type="daily_report",
    report_type="daily",
    format="json",
    status="completed",
    parameters={
        "test": "data",
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat()
    },
    file_path="/path/to/test/report.json"
)
```

## Integration Test Types

### API Integration Tests

API integration tests verify that the API endpoints work correctly with the database and other components. These tests include:

1. **Reports Workflow Test**: Tests the complete workflow for reports, including creating a report, getting a report, generating a report, and getting the report list.
2. **Detections Workflow Test**: Tests the complete workflow for detections, including getting the list of detections, filtering detections by station, and searching for detections.
3. **Analytics Workflow Test**: Tests the complete workflow for analytics, including getting the analytics overview and getting the analytics stats.

### Detection System Integration Tests

Detection system integration tests verify that the detection system works correctly with the database and other components. These tests include:

1. **Detection Pipeline Test**: Tests the complete detection pipeline, including creating a sample audio, processing the audio through the feature extractor, processing the features through the track manager, and verifying the detection is saved in the database.
2. **Hierarchical Detection Test**: Tests the hierarchical detection process, including trying local detection, MusicBrainz detection, and Audd detection.
3. **Play Duration Tracking Test**: Tests the tracking of play duration for songs on stations, ensuring that the system captures and records the exact duration of each song played on each station.

   Ces tests suivent le cycle complet de détection en utilisant des données réelles de stations de radio sénégalaises. Ils vérifient que :
   - La durée exacte de lecture est capturée à partir des flux audio
   - La durée est correctement enregistrée dans la base de données
   - Les statistiques sont mises à jour avec les durées précises
   - Les durées peuvent varier entre différentes stations

   Une amélioration majeure récente est la capacité de capturer l'audio jusqu'à ce que le son s'arrête naturellement, en détectant les silences ou les changements significatifs dans le contenu audio. Cette approche garantit que la durée exacte de chaque morceau est mesurée, du début jusqu'à la fin naturelle, sans se limiter à une durée prédéfinie.

   Pour plus de détails, voir [Play Duration Integration Testing](play_duration_integration_testing.md).

### Analytics System Integration Tests

Analytics system integration tests verify that the analytics system works correctly with the database and other components. These tests include:

1. **Stats Calculation Test**: Tests the calculation of statistics, including creating test data, calculating statistics, and verifying the statistics are correct.
2. **Analytics Data Generation Test**: Tests the generation of analytics data, including creating test data, generating analytics data, and verifying the analytics data is correct.

## Running Integration Tests

To run all integration tests:

```bash
python -m pytest -xvs backend/tests/integration/
```

To run tests for a specific component:

```bash
python -m pytest -xvs backend/tests/integration/api/
python -m pytest -xvs backend/tests/integration/detection/
python -m pytest -xvs backend/tests/integration/analytics/
```

To run a specific test:

```bash
python -m pytest -xvs backend/tests/integration/api/test_api_integration.py::TestAPIIntegration::test_reports_workflow
```

## Best Practices

- Keep tests focused on integration between components
- Use fixtures to set up the test environment
- Clean up test data after the test is run
- Use descriptive test names
- Add comments to explain the test steps
- Use assertions to verify the expected behavior

## Integration Test Coverage

Integration tests should cover the following areas:

1. **API Endpoints**: All API endpoints should be tested to ensure they work correctly with the database and other components.
2. **Detection System**: The detection system should be tested to ensure it works correctly with the database and other components.
3. **Analytics System**: The analytics system should be tested to ensure it works correctly with the database and other components.
4. **Authentication**: Authentication should be tested to ensure it works correctly with the API endpoints.
5. **Error Handling**: Error handling should be tested to ensure the system responds correctly to errors.

## Integration Test Maintenance

Integration tests should be maintained as the system evolves. When new features are added or existing features are modified, the integration tests should be updated to reflect these changes.

## Known Issues and Solutions

### Router Order and Endpoint Conflicts

When testing API endpoints with similar URL patterns, be aware of the router inclusion order in the main application. In our testing, we discovered that the order of router inclusion in `main.py` can affect which endpoint handles a request.

**Issue**: The `/api/{id}` endpoint was being handled by the detections router instead of the channels router because the detections router was included before the channels router in `main.py`.

**Solution**: For testing specific endpoints, use the correct nested path structure. For example:

- Reports endpoints should use `/api/reports/reports/` instead of `/api/reports/`
- Report by ID should use `/api/reports/reports/{id}` instead of `/api/reports/{id}`

This ensures that the request is routed to the correct handler, regardless of the router inclusion order.

### Authentication in Tests

Some tests are intentionally skipped due to authentication requirements. This is expected behavior and not a test failure.

**Issue**: Tests that require authentication may fail with a 401 Unauthorized status code if the authentication headers are not properly set up or if the authentication mechanism is mocked incorrectly.

**Solution**:
1. Use the `auth_headers` fixture provided in `conftest.py` for tests that require authentication:
   ```python
   def test_authenticated_endpoint(test_client: TestClient, auth_headers: Dict[str, str]):
       response = test_client.get("/api/protected-endpoint", headers=auth_headers)
       assert response.status_code == 200
   ```

2. For tests that specifically test authentication failure, you can intentionally omit the headers:
   ```python
   def test_authentication_required(test_client: TestClient):
       response = test_client.get("/api/protected-endpoint")
       assert response.status_code == 401
   ```

3. If a test is skipped with `pytest.skip("Skipping due to authentication issues")`, it means the test is not yet ready to be run due to authentication complexities. These tests should be revisited when the authentication mechanism is more stable.

### Schema and Model Field Mismatches

Be aware of potential mismatches between database models and Pydantic schemas. Fields present in the database model might not be included in the response schema.

**Issue**: The `RadioStation` model includes a `country` field, but the `StationResponse` schema does not include this field, causing a `KeyError` when trying to access it in tests.

**Solution**: Always check the response schema definition before asserting fields in the response:

```python
# Verify only the fields defined in the schema
assert data["id"] == test_station.id
assert data["name"] == test_station.name
assert data["stream_url"] == test_station.stream_url
assert data["is_active"] == test_station.is_active
# Do not assert fields not in the schema, like "country"
```

## Handling Deprecation Warnings

### Pydantic Deprecation Warnings

Pydantic v2.0 introduced several breaking changes, including the deprecation of `json_encoders`. These warnings need to be addressed before upgrading to Pydantic v3.0.

**Issue**: The `json_encoders` configuration option is deprecated in Pydantic v2.0 and will be removed in v3.0.

**Solution**: Replace `json_encoders` with the new `model_serializer` decorator:

```python
# Before
class MyModel(BaseModel):
    created_at: datetime
    duration: timedelta

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            timedelta: lambda v: v.total_seconds() if v else None
        }
    )

# After
class MyModel(BaseModel):
    created_at: datetime
    duration: timedelta

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        data = self.model_dump()
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.duration:
            data["duration"] = self.duration.total_seconds()
        return data
```

### pytest-asyncio Deprecation Warnings

pytest-asyncio has deprecated the default event loop scope configuration.

**Issue**: The warning `asyncio_default_fixture_loop_scope` configuration option is deprecated and will be removed in a future version.

**Solution**:
1. Update the event loop fixture to use the recommended approach:
   ```python
   @pytest.fixture(scope="function")
   def event_loop():
       """Create an event loop for async tests."""
       policy = asyncio.get_event_loop_policy()
       loop = policy.new_event_loop()
       yield loop
       loop.close()
   ```

2. Add a pytest.ini file with the proper configuration:
   ```ini
   [pytest]
   asyncio_mode = auto

   [pytest-asyncio]
   asyncio_mode = auto
   ```

These changes ensure that the tests will continue to work with future versions of Pydantic and pytest-asyncio.

## Testing with Real Data

Integration tests can be enhanced by using real audio data to test the detection system. This approach provides more realistic testing scenarios and helps identify issues that might not be caught with mock data.

### Setting Up Real Data Tests

1. **Create a Test Data Directory**

   Create a directory for storing test audio files:

   ```
   backend/tests/data/audio/
   ```

2. **Add Sample Audio Files**

   Add sample audio files to the test data directory. These files should be short clips (5-10 seconds) of music that can be used for testing the detection system.

   Example file structure:

   ```
   backend/tests/data/audio/
   ├── sample1.mp3       # Known track for local detection
   ├── sample2.mp3       # Track for MusicBrainz detection
   ├── sample3.mp3       # Track for Audd detection
   └── speech_sample.mp3 # Speech sample for testing speech detection
   ```

3. **Create a Fixture for Real Audio Data**

   Add a fixture to `conftest.py` that loads the real audio data:

   ```python
   @pytest.fixture
   def real_audio_data():
       """Load real audio data for testing."""
       audio_path = os.path.join(os.path.dirname(__file__), "data", "audio", "sample1.mp3")
       with open(audio_path, "rb") as f:
           return f.read()
   ```

4. **Use Real Data in Tests**

   Update the tests to use the real audio data:

   ```python
   @pytest.mark.asyncio
   async def test_real_audio_detection(self, db_session: Session, real_audio_data: bytes):
       """Test detection with real audio data."""
       # Test implementation using real_audio_data
   ```

### Best Practices for Real Data Testing

1. **Keep Test Files Small**: Use short audio clips (5-10 seconds) to keep tests fast.
2. **Include Diverse Samples**: Include different types of music and speech to test various scenarios.
3. **Document Sample Sources**: Document the source of each sample file and any licensing information.
4. **Version Control**: Include test audio files in version control to ensure consistent test results.
5. **Parameterize Tests**: Use pytest's parameterization to run the same test with different audio samples.

### Example: Testing with Real Audio

Here's an example of a test that uses real audio data:

```python
@pytest.mark.asyncio
async def test_real_audio_detection(self, db_session: Session, real_audio_data: bytes):
    """Test detection with real audio data."""
    # Create a test station
    station = RadioStation(
        name="Real Audio Test Station",
        stream_url="http://test.stream/real",
        status="active"
    )
    db_session.add(station)
    db_session.commit()

    # Create the audio processor
    audio_processor = AudioProcessor(db_session)

    # Process the real audio data
    features = audio_processor.extract_features(real_audio_data)

    # Detect the track
    detection_result = await audio_processor.detect_track(features, station.id)

    # Verify the detection
    assert detection_result is not None, "No track detected"
    assert detection_result.confidence > 0.7, "Low confidence detection"

    # Verify the detection was saved in the database
    saved_detection = db_session.query(TrackDetection).filter(
        TrackDetection.station_id == station.id
    ).order_by(TrackDetection.detected_at.desc()).first()

    assert saved_detection is not None, "Detection not saved in the database"
    assert saved_detection.confidence > 0.7, "Detection confidence not correct"
```

This approach provides more realistic testing of the detection system and helps ensure that it works correctly with real audio data.

## Conclusion

Integration testing is an essential part of the testing strategy for the SODAV Monitor project. By verifying that different components of the system work together correctly, integration tests help ensure that the system functions as expected in real-world scenarios.
