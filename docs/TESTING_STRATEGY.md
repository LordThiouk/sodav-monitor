# Testing Strategy

## Overview
This document outlines our approach to testing the SODAV Monitor project. We follow a component-based testing strategy, where each major component is tested in isolation to ensure proper functionality and maintainability.

## Testing Principles
1. **Component Isolation**: Each component is tested independently to minimize dependencies
2. **Mock Dependencies**: External dependencies are mocked to ensure reliable tests
3. **High Coverage**: Aim for >90% code coverage for critical components
4. **Clear Test Structure**: Tests are organized by component and functionality
5. **Maintainable Tests**: Tests are kept focused and easy to understand

## Component Testing Structure
Each component has its own test directory with the following structure:
```
tests/
├── component_name/
│   ├── __init__.py
│   ├── conftest.py          # Component-specific fixtures
│   └── test_component.py    # Component tests
```

## Authentication Module Testing
The authentication module (`utils/auth`) was successfully tested in isolation with 91% code coverage.

### Test Structure
```
tests/auth/
├── __init__.py
├── conftest.py              # Auth-specific fixtures
└── test_auth.py            # Auth tests
```

### Key Testing Strategies
1. **Settings Override**: Used dependency injection to override settings
   ```python
   TEST_SETTINGS = {
       'SECRET_KEY': "test_secret_key",
       'ALGORITHM': "HS256",
       'ACCESS_TOKEN_EXPIRE_MINUTES': 15
   }
   ```

2. **Database Mocking**: Mocked database sessions and queries
   ```python
   @pytest.fixture
   def mock_db_session():
       session = Mock()
       session.query = Mock()
       session.query.return_value.filter.return_value.first = Mock()
       return session
   ```

3. **Test Cases**:
   - Password verification
   - Password hashing
   - Token creation
   - Token validation
   - Error handling

### Test Isolation
- Used `confcutdir` in pytest.ini to isolate component tests
- Created minimal fixtures in component-specific conftest.py
- Avoided loading unnecessary dependencies

### Results
- All auth tests passing
- 91% code coverage
- Clear error handling
- Maintainable test suite

## Stream Handler Testing (Completed)
The stream handler module (`detection/audio_processor/stream_handler.py`) has been successfully tested with comprehensive coverage.

### Test Structure
```
tests/stream_handler/
├── __init__.py
├── conftest.py              # Stream handler fixtures
└── test_stream_handler.py   # Stream handler tests
```

### Key Testing Strategies
1. **Buffer Management**:
   - Buffer initialization and validation
   - Chunk processing and overflow handling
   - Buffer reset and cleanup

2. **Performance Testing**:
   - Processing latency benchmarks
   - Memory usage monitoring
   - Concurrent stream handling

3. **Error Handling**:
   - Invalid input validation
   - Buffer overflow recovery
   - Error state management

### Results
- All stream handler tests passing
- Processing latency < 100ms
- Memory usage < 50MB
- Robust error handling

## Feature Extractor Testing (Completed)
The feature extractor module (`detection/audio_processor/feature_extractor.py`) has been successfully tested.

### Test Structure
```
tests/feature_extractor/
├── __init__.py
├── conftest.py              # Feature extractor fixtures
└── test_feature_extractor.py
```

### Key Testing Strategies
1. **Audio Analysis**:
   - Feature extraction validation
   - Music vs. speech detection
   - Signal processing accuracy

2. **Performance**:
   - Processing efficiency
   - Memory optimization
   - Batch processing

### Results
- Accurate feature extraction
- Reliable music detection
- Efficient memory usage

## Analytics Manager Testing (In Progress)
The analytics manager module (`utils/analytics/analytics_manager.py`) is currently being tested.

### Test Structure
```
tests/analytics/
├── __init__.py
├── conftest.py              # Analytics fixtures
└── test_analytics_manager.py
```

### Implementation Status
- Basic test structure created
- Transaction management tests implemented
- Performance benchmarks in progress
- Error handling tests completed

## Music Detection Testing Strategy

### Test Structure
```
tests/detection/
├── audio_processor/
│   ├── test_feature_extractor.py   # Feature extraction tests
│   ├── test_audio_analysis.py      # Audio analysis tests
│   └── test_recognition_core.py    # Recognition pipeline tests
└── test_detection.py               # Integration tests
```

### Key Testing Strategies
1. **Feature Extraction Testing**
   - Test with synthetic audio signals
   - Validate feature ranges and shapes
   - Check for NaN/Inf values
   - Verify memory usage
   - Benchmark performance

2. **Music Detection Testing**
   - Test with pure musical signals
   - Test with speech content
   - Test with mixed content
   - Test with noise
   - Test with silence
   - Validate confidence scores

3. **Edge Cases**
   - Extremely short audio
   - Very long audio
   - Invalid audio data
   - Corrupted audio
   - DC offset
   - Extreme amplitude values

4. **Performance Testing**
   - Processing time benchmarks
   - Memory usage monitoring
   - Concurrent processing
   - Resource cleanup

### Results
- Feature extraction tests passing
- Music detection accuracy > 95%
- Edge case handling robust
- Performance within targets

## Data Persistence Testing Strategy

### Test Structure
```
tests/
├── models/
│   └── test_database.py    # Database model tests
└── analytics/
    └── test_analytics.py   # Analytics data tests
```

### Key Testing Strategies
1. **Model Testing**
   - Test model creation
   - Validate relationships
   - Check constraints
   - Test cascade behavior
   - Verify indexes

2. **Data Integrity**
   - Test transaction handling
   - Check constraint violations
   - Verify cascade updates
   - Test data cleanup

3. **Analytics Testing**
   - Test data aggregation
   - Verify metric calculations
   - Check time-based grouping
   - Test report generation

4. **Performance Testing**
   - Query performance
   - Bulk operation handling
   - Index effectiveness
   - Memory usage

### Results
- Model tests passing
- Data integrity maintained
- Analytics calculations accurate
- Performance meeting targets

## API Testing Strategy

### Current Progress
We have successfully fixed several API test issues:

1. **Channel API Tests Fixed**
   - ✅ `test_get_stations_with_filters`: Fixed by ensuring proper test station data and transaction management
   - ✅ `test_update_station`: Fixed by wrapping update data in `station_update` field
   - ✅ `test_update_nonexistent_station`: Fixed request format to match API expectations

### Next Focus: Detections API
The next component to test is the Detections API, which includes:

1. **Core Functionality**
   - Get all detections
   - Filter detections by station/track
   - Pagination support
   - Create new detections
   - Delete detections

2. **Test Cases**:
```python
def test_get_detections(client: TestClient, auth_headers: Dict[str, str], test_detection: TrackDetection):
    """Test retrieving all detections."""
    response = client.get("/api/detections/", headers=auth_headers)
    assert response.status_code == 200
```

### Progress Tracking
- ✅ Authentication endpoints
- ✅ Channel management endpoints
- ⬜ Detection endpoints
- ⬜ Analytics endpoints
- ⬜ Report generation endpoints

## Running API Tests
To run API tests specifically:
```bash
pytest tests/api/test_api.py -v
```

To run a specific test case:
```bash
pytest tests/api/test_api.py::TestAuthAPI::test_login_success -v
```

## Running Tests
To run tests for specific components:
```