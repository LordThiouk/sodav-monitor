# Integration Tests for SODAV Monitor

This directory contains integration tests for the SODAV Monitor backend. These tests verify that different components of the system work together correctly.

## Structure

The integration tests are organized by component:

```
integration/
├── api/                     # API integration tests
│   ├── test_api_integration.py
│   └── test_api_endpoints.py
├── detection/               # Detection system integration tests
│   ├── test_detection_integration.py
│   └── test_detection_pipeline.py
├── analytics/               # Analytics system integration tests
│   ├── test_analytics_integration.py
│   └── test_analytics_pipeline.py
├── conftest.py              # Shared fixtures for integration tests
└── README.md                # This file
```

## Running the Tests

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
python -m pytest -xvs backend/tests/integration/api/test_api_endpoints.py::TestAPIEndpoints::test_get_stations
```

## Test Fixtures

The integration tests use fixtures defined in `conftest.py` to set up the test environment. These fixtures include:

- `db_session`: A database session for the tests
- `test_user`: A test user for authentication
- `auth_headers`: Authentication headers for API requests
- `test_client`: A test client for making API requests

## Test Data

The integration tests create test data in the database as needed. This data is cleaned up after the tests are run to avoid polluting the database.

## Test Descriptions

### Detection Tests

#### `test_detection_integration.py`
- Tests the basic detection functionality
- Verifies that detections are saved in the database

#### `test_detection_pipeline.py`
- Tests the complete detection pipeline
- Verifies the hierarchical detection process (local → MusicBrainz → Audd)
- Tests speech detection
- Tests error handling

### Analytics Tests

#### `test_analytics_integration.py`
- Tests the basic analytics functionality
- Verifies that analytics data is generated correctly

#### `test_analytics_pipeline.py`
- Tests the complete analytics pipeline
- Verifies that statistics are updated after detections
- Tests track, artist, station, and station-track statistics
- Tests analytics data generation

### API Tests

#### `test_api_integration.py`
- Tests the basic API functionality
- Verifies that API endpoints return the expected data

#### `test_api_endpoints.py`
- Tests all API endpoints
- Verifies that API endpoints work correctly with the detection and analytics systems
- Tests report generation and retrieval

## Adding New Tests

To add a new integration test:

1. Identify the component you want to test
2. Create a new test file in the appropriate directory
3. Define a test class and test methods
4. Use the fixtures defined in `conftest.py` as needed
5. Clean up any test data created during the test

## Best Practices

- Keep tests focused on integration between components
- Use fixtures to set up the test environment
- Clean up test data after the test is run
- Use descriptive test names
- Add comments to explain the test steps
- Use assertions to verify the expected behavior 