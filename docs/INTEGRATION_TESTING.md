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
│   └── test_detection_integration.py
├── analytics/               # Analytics system integration tests
│   └── test_analytics_integration.py
├── conftest.py              # Shared fixtures for integration tests
└── README.md                # Documentation for integration tests
```

## Test Fixtures

Integration tests use fixtures defined in `conftest.py` to set up the test environment. These fixtures include:

- `db_session`: A database session for the tests
- `test_user`: A test user for authentication
- `auth_headers`: Authentication headers for API requests
- `test_client`: A test client for making API requests

## Test Data

Integration tests create test data in the database as needed. This data is cleaned up after the tests are run to avoid polluting the database.

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

## Conclusion

Integration testing is an essential part of the testing strategy for the SODAV Monitor project. By verifying that different components of the system work together correctly, integration tests help ensure that the system functions as expected in real-world scenarios. 