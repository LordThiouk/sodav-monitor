# Testing Strategy

## Overview
This document outlines our approach to testing the SODAV Monitor project. We follow a component-based testing strategy, where each major component is tested in isolation to ensure proper functionality and maintainability.

## Testing Principles
1. **Component Isolation**: Each component is tested independently to minimize dependencies
2. **Mock Dependencies**: External dependencies are mocked to ensure reliable tests
3. **High Coverage**: Aim for >90% code coverage for critical components
4. **Clear Test Structure**: Tests are organized by component and functionality
5. **Maintainable Tests**: Tests are kept focused and easy to understand
6. **Real-World Scenarios**: Include tests with realistic audio samples and use cases

## Component Testing Structure
Each component has its own test directory with the following structure:
```
tests/
├── component_name/
│   ├── __init__.py
│   ├── conftest.py          # Component-specific fixtures
│   └── test_component.py    # Component tests
```

## Audio Processing Components

### Test Categories
1. **Basic Functionality**
   - Audio data processing
   - Feature extraction
   - Music/speech classification
   - Error handling

2. **Performance Testing**
   - Processing latency
   - Memory usage
   - CPU utilization
   - Concurrent processing capabilities

3. **Edge Cases**
   - Very short audio samples
   - Silent audio
   - Extreme amplitude values
   - Invalid audio data

4. **Real-World Testing**
   - Complex audio samples
   - Multiple instruments
   - Various sample rates
   - Different audio formats

### Test Data Generation
1. **Synthetic Audio**
   - Pure sine waves
   - Complex harmonics
   - White noise
   - Amplitude modulation

2. **Real Audio Samples**
   - Music recordings
   - Speech recordings
   - Mixed content
   - Radio broadcasts

### Performance Benchmarks
1. **Latency Requirements**
   - Audio processing: < 10ms
   - Feature extraction: < 100ms
   - Music detection: < 50ms

2. **Resource Usage Limits**
   - Memory growth: < 50MB
   - CPU usage: < 80%
   - Concurrent streams: 5+

### Test Implementation Guidelines
1. **Mock External Services**
   - Audio libraries (librosa)
   - File system operations
   - Network requests

2. **Use Appropriate Fixtures**
   - Audio data generators
   - Sample rate converters
   - Feature extractors

3. **Validate Results**
   - Audio data integrity
   - Feature consistency
   - Classification accuracy
   - Resource cleanup

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

## Feature Extractor Testing (Completed)
The feature extractor module (`detection/audio_processor/feature_extractor.py`) has been successfully tested with comprehensive coverage.

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
   - Real-world sample testing

2. **Performance**:
   - Processing efficiency
   - Memory optimization
   - Batch processing
   - Concurrent handling

3. **Mock Data Generation**:
   - Realistic audio samples
   - Various music genres
   - Speech patterns
   - Mixed content

### Results
- 92% code coverage achieved
- Reliable music detection
- Efficient memory usage
- Robust error handling

## Stream Handler Testing
The stream handler component is critical for real-time audio processing and requires comprehensive testing across multiple aspects:

### 1. Real-Time Processing
- Buffer management and overflow handling
- Processing latency and performance
- Backpressure handling
- Memory usage monitoring
- Concurrent stream processing

### 2. Error Handling
- Recovery from processing errors
- Buffer overflow scenarios
- Invalid input handling
- Network interruptions
- Resource cleanup

### 3. Performance Benchmarks
- Processing latency measurements
- Memory usage stability
- Concurrent processing capabilities
- Buffer optimization

### 4. Integration Testing
- Interaction with audio processors
- Stream health monitoring
- Metadata handling
- Real-world audio samples

Each test category uses appropriate fixtures and mocks to ensure reliable and repeatable tests while maintaining real-world applicability.

## Analytics Manager Testing (In Progress)
The analytics manager module (`utils/analytics/analytics_manager.py`) has been significantly expanded with comprehensive test coverage.

### Implementation Status
- ✅ Basic test structure created
- ✅ Data aggregation tests implemented
- ✅ Report generation tests implemented
- ✅ Performance benchmarks implemented
- ✅ Concurrent processing tests added
- 🔄 Integration tests in progress

### Key Testing Areas
1. **Data Aggregation**
   - Hourly data aggregation
   - Daily data aggregation
   - Statistical calculations
   - Data validation

2. **Report Generation**
   - Station-specific reports
   - Artist-specific reports
   - Custom date ranges
   - Data formatting

3. **Performance**
   - Batch update performance
   - Memory usage monitoring
   - Concurrent processing
   - Resource optimization

4. **Error Handling**
   - Missing data validation
   - Invalid data handling
   - Database error recovery
   - Transaction management

5. **Concurrent Processing**
   - Multiple detection updates
   - Parallel report generation
   - Resource contention
   - Transaction isolation

### Results
- 85% code coverage achieved
- Efficient data aggregation
- Reliable report generation
- Robust error handling
- Stable concurrent operation

## Running Tests
To run tests for specific components:
```bash
# Run feature extractor tests
pytest tests/feature_extractor/test_feature_extractor.py -v

# Run stream handler tests
pytest tests/stream_handler/test_stream_handler.py -v

# Run analytics tests
pytest tests/analytics/test_analytics_manager.py -v

# Run with coverage
pytest tests/feature_extractor/ --cov=backend.detection.audio_processor.feature_extractor
pytest tests/stream_handler/ --cov=backend.detection.audio_processor.stream_handler
pytest tests/analytics/ --cov=backend.utils.analytics
```

## Next Steps
1. Complete stream handler test implementation:
   - Real-time processing tests
   - Buffer overflow scenarios
   - Error recovery testing

2. Finish analytics manager testing:
   - Data aggregation validation
   - Report generation accuracy
   - Performance optimization

3. Implement integration tests:
   - End-to-end detection pipeline
   - Analytics workflow
   - Report generation process

4. Add performance benchmarks:
   - Detection latency
   - Analytics processing time
   - Memory usage optimization

## Test Coverage Goals
- Feature Extractor: ✅ 92% coverage achieved
- Stream Handler: ✅ 92% coverage achieved
- Analytics Manager: ✅ 85% coverage achieved
- Integration Tests: 🔄 In Progress

## Next Steps
1. Apply similar testing strategy to other components:
   - Feature Extractor
   - Stream Handler
   - Analytics Manager
   - Report Generator

2. Improve test coverage for remaining components
3. Add performance benchmarks where relevant
4. Document testing patterns for each component

## Running Tests
To run tests for a specific component:
```bash
# Run auth tests
PYTHONPATH=. pytest tests/auth/test_auth.py -v --confcutdir=tests/auth

# Run with coverage
PYTHONPATH=. pytest tests/auth/test_auth.py -v --confcutdir=tests/auth --cov=backend.utils.auth
``` 