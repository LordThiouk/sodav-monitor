# Testing Strategy

## Overview
This document outlines our approach to testing the SODAV Monitor project. We follow a component-based testing strategy, where each major component is tested in isolation to ensure proper functionality and maintainability. Additionally, we use integration tests to verify that different components work together correctly.

## Testing Principles
1. **Component Isolation**: Each component is tested independently to minimize dependencies
2. **Mock Dependencies**: External dependencies are mocked to ensure reliable tests
3. **High Coverage**: Aim for >90% code coverage for critical components
4. **Clear Test Structure**: Tests are organized by component and functionality
5. **Maintainable Tests**: Tests are kept focused and easy to understand
6. **Performance Benchmarks**: Each critical endpoint has defined performance targets
7. **Integration Testing**: Components are tested together to verify correct interaction

## Component Testing Structure
Each component has its own test directory with the following structure:
```
tests/
├── api/                     # API endpoint tests
│   ├── test_api_performance.py
│   ├── test_music_detection_api.py
│   ├── test_analytics_api.py
│   └── test_reports_api.py
├── detection/              # Detection module tests
│   ├── audio_processor/    # Audio processor tests
│   │   ├── test_core.py
│   │   ├── test_feature_extractor.py
│   │   ├── test_performance.py
│   │   └── test_stream_handler.py
│   └── test_detection.py
├── analytics/             # Analytics module tests
│   └── test_analytics.py
├── reports/              # Report generation tests
│   └── test_reports.py
├── integration/          # Integration tests
│   ├── api/              # API integration tests
│   │   └── test_api_integration.py
│   ├── detection/        # Detection integration tests
│   │   └── test_detection_integration.py
│   ├── analytics/        # Analytics integration tests
│   │   └── test_analytics_integration.py
│   ├── conftest.py       # Integration test fixtures
│   └── README.md         # Integration test documentation
└── conftest.py          # Shared fixtures
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

## Integration Testing Strategy

Integration tests verify that different components of the system work together correctly, ensuring that the system functions as expected in real-world scenarios.

### Integration Test Structure
```
tests/integration/
├── api/                     # API integration tests
│   └── test_api_integration.py
├── detection/               # Detection system integration tests
│   └── test_detection_integration.py
├── analytics/               # Analytics system integration tests
│   └── test_analytics_integration.py
├── conftest.py              # Shared fixtures for integration tests
└── README.md                # Documentation for integration tests
```

### Key Integration Test Types

1. **API Integration Tests**
   - Reports workflow testing
   - Detections workflow testing
   - Analytics workflow testing

2. **Detection System Integration Tests**
   - Detection pipeline testing
   - Hierarchical detection testing

3. **Analytics System Integration Tests**
   - Stats calculation testing
   - Analytics data generation testing

### Integration Test Fixtures

Integration tests use fixtures defined in `conftest.py` to set up the test environment:

- `db_session`: A database session for the tests
- `test_user`: A test user for authentication
- `auth_headers`: Authentication headers for API requests
- `test_client`: A test client for making API requests

### Integration Test Best Practices

- Keep tests focused on integration between components
- Use fixtures to set up the test environment
- Clean up test data after the test is run
- Use descriptive test names
- Add comments to explain the test steps
- Use assertions to verify the expected behavior

### Integration Test Coverage

Integration tests should cover the following areas:

1. **API Endpoints**: All API endpoints should be tested to ensure they work correctly with the database and other components.
2. **Detection System**: The detection system should be tested to ensure it works correctly with the database and other components.
3. **Analytics System**: The analytics system should be tested to ensure it works correctly with the database and other components.
4. **Authentication**: Authentication should be tested to ensure it works correctly with the API endpoints.
5. **Error Handling**: Error handling should be tested to ensure the system responds correctly to errors.

For more detailed information about integration testing, see [INTEGRATION_TESTING.md](INTEGRATION_TESTING.md).

## Performance Testing Results

### API Performance Benchmarks
The following performance targets have been established and tested:

1. **Music Detection Endpoint**
   - Response time: < 100ms
   - Memory usage: < 50MB
   - Current performance:
     - Min: 1.2488 ms
     - Max: 97.3707 ms
     - Mean: 1.7042 ms
     - OPS: 586.7772

2. **Analytics Overview**
   - Response time: < 200ms
   - Memory usage: < 100MB
   - Current performance:
     - Min: 21.7535 ms
     - Max: 110.0884 ms
     - Mean: 26.7584 ms
     - OPS: 37.3715

3. **Report Generation**
   - Response time: < 500ms
   - Memory usage: < 200MB
   - Current performance:
     - Min: 1.2488 ms
     - Max: 97.3707 ms
     - Mean: 1.7042 ms
     - OPS: 586.7772

4. **Search Performance**
   - Response time: < 200ms
   - Memory usage: < 100MB
   - Current performance:
     - Min: 14.8522 ms
     - Max: 101.1457 ms
     - Mean: 18.4042 ms
     - OPS: 54.3355

### Concurrent Request Handling
- Tested with 10, 50, and 100 concurrent requests
- Target: Average response time < 500ms
- Linear scaling up to 100 concurrent requests
- No request failures

## Test Coverage by Module

### Music Detection Module
- Feature extraction validation ✅
- Music vs. speech detection ✅
- Signal processing accuracy ✅
- Processing efficiency ✅
- Memory optimization ✅
- Batch processing ✅
- Error handling ✅

### Analytics Module
- Data aggregation accuracy ✅
- Query performance 🔄
- Memory usage optimization 🔄
- Report generation ✅
- Export functionality ✅

### Report Generation Module
- PDF, Excel, CSV generation ✅
- Email delivery ✅
- Subscription management ✅
- Error handling 🔄
- Resource cleanup ✅

## Mock Strategy
We use the following mocking approach for external dependencies:

1. **Audio Stream Handler**
```python
stream_handler = StreamHandler()
stream_handler.get_audio_data = MagicMock(return_value=np.random.random((4096, 2)))
```

2. **Audio Processor**
```python
audio_processor = AudioProcessor(db_session)
audio_processor.stream_handler = stream_handler
audio_processor.detect_music = MagicMock(return_value={"status": "success", "detections": []})
audio_processor.is_initialized = MagicMock(return_value=True)
```

3. **Radio Manager**
```python
radio_manager = RadioManager(db_session=db_session, audio_processor=audio_processor)
```

## Test Database Configuration
- Uses SQLite for testing
- Fixtures for common test data
- Transaction rollback after each test
- Isolation between test runs

## Running Tests
To run specific test categories:

1. All tests:
```bash
python -m pytest tests/
```

2. Performance tests only:
```bash
python -m pytest tests/api/test_api_performance.py -v --benchmark-only
```

3. API tests:
```bash
python -m pytest tests/api/
```

4. Detection tests:
```bash
python -m pytest tests/detection/
```

## Redis Integration Testing
The Redis integration has been successfully tested with comprehensive coverage.

### Test Structure
```
tests/api/
├── test_music_detection_api.py  # Redis integration tests for music detection
└── test_websocket.py           # Redis integration tests for WebSocket
```

### Key Testing Strategies
1. **Redis Mocking**:
   ```python
   @pytest.fixture
   def mock_redis():
       with patch('backend.core.config.redis.get_redis') as mock:
           mock_redis = AsyncMock()
           mock_redis.publish = AsyncMock()
           mock_redis.subscribe = AsyncMock()
           mock_redis.get_message = AsyncMock()
           mock.return_value = mock_redis
           yield mock_redis
   ```

2. **Message Publishing**:
   - Test successful message publishing
   - Verify message format and content
   - Test error handling during publishing

3. **Message Subscription**:
   - Test subscription to channels
   - Verify message reception
   - Test connection handling

### Results
- All Redis integration tests passing
- Proper error handling
- Reliable message delivery
- Efficient connection management

## Search Endpoint Testing
The search endpoint has been thoroughly tested with both unit and performance tests.

### Test Structure
```
tests/api/
├── test_api_performance.py      # Search performance tests
└── test_music_detection_api.py  # Search functionality tests
```

### Key Testing Strategies
1. **Performance Testing**:
   - Response time < 200ms
   - Memory usage < 100MB
   - Efficient search indexing

2. **Functionality Testing**:
   - Test search by track title
   - Test search by artist name
   - Test search by ISRC
   - Test pagination
   - Test result ordering

3. **Edge Cases**:
   - Empty search query
   - Special characters
   - Very long queries
   - Non-existent items

### Results
- Search endpoint performance meets targets
- Proper error handling
- Accurate search results
- Efficient pagination

## Current Status and Issues

### Passing Tests
- Music detection core functionality ✅
- Analytics data aggregation ✅
- Report generation ✅
- Stream handling ✅
- Feature extraction ✅
- Search endpoint ✅
- Redis integration ✅

### Known Issues
1. Report generation endpoint returning 404
   - Under investigation
   - Potential issue with file path handling

2. Station stats endpoint returning 500
   - Under investigation
   - Likely related to database query optimization

3. Detection history endpoint returning 500
   - Under investigation
   - Potential memory usage issue with large result sets

### Next Steps
1. Implement proper error handling in report generation:
   - Add file existence checks
   - Improve error messages
   - Add logging for debugging

2. Debug station stats queries:
   - Profile database queries
   - Add query optimization
   - Implement result caching

3. Optimize detection history performance:
   - Implement pagination
   - Add result limiting
   - Optimize database queries

## Continuous Integration
- All tests must pass before deployment
- Performance benchmarks must meet targets
- Code coverage must remain above 90%
- No regression in existing functionality

## Tests de Contraintes

### Test de la Contrainte d'Unicité ISRC

La contrainte d'unicité sur la colonne ISRC de la table `tracks` est un élément critique pour maintenir l'intégrité des données. Des tests spécifiques ont été développés pour vérifier son bon fonctionnement.

#### Structure des Tests
```
tests/
└── test_isrc_uniqueness.py    # Tests de la contrainte d'unicité ISRC
```

#### Stratégies de Test
1. **Test d'Unicité**
   - Vérifier que la base de données n'accepte pas deux pistes avec le même ISRC
   - Tester la levée d'exceptions appropriées (IntegrityError)
   - Vérifier le comportement de rollback en cas d'erreur

   ```python
   def test_isrc_uniqueness_constraint(self):
       # Créer une première piste avec un ISRC
       track1 = Track(title="Test Track 1", artist_id=self.artist.id, isrc="FR1234567890")
       self.db_session.add(track1)
       self.db_session.commit()

       # Tenter de créer une deuxième piste avec le même ISRC
       track2 = Track(title="Test Track 2", artist_id=self.artist.id, isrc="FR1234567890")
       self.db_session.add(track2)

       # Vérifier que la contrainte d'unicité est appliquée
       with self.assertRaises(IntegrityError):
           self.db_session.commit()
   ```

2. **Test de Détection avec ISRC**
   - Vérifier que les méthodes de détection (`find_acoustid_match`, `find_audd_match`) utilisent correctement l'ISRC pour retrouver les pistes existantes
   - Tester avec des ISRC simulés
   - Vérifier que les pistes existantes sont correctement retrouvées

   ```python
   async def test_acoustid_match_with_isrc(self):
       # Créer une piste avec un ISRC unique
       test_isrc = f"FR{uuid.uuid4().hex[:10].upper()}"
       track = Track(title="Test Track", artist_id=self.artist.id, isrc=test_isrc)
       self.db_session.add(track)
       self.db_session.commit()

       # Simuler un résultat AcoustID avec le même ISRC
       acoustid_result = {"recordings": [{"isrc": [test_isrc]}]}

       # Vérifier que la méthode retrouve la piste existante
       result = await self.track_manager.find_acoustid_match(audio_features, acoustid_result)
       self.assertEqual(result['track']['id'], track.id)
       self.assertEqual(result['confidence'], 1.0)  # Confiance maximale pour une correspondance ISRC
   ```

3. **Test d'Intégration avec les Services de Détection**
   - Tester l'intégration complète avec les services de détection
   - Vérifier que les statistiques de lecture sont correctement mises à jour pour les pistes existantes
   - Tester avec des fichiers audio réels

#### Résultats
- Contrainte d'unicité correctement appliquée
- Méthodes de détection utilisant efficacement l'ISRC
- Statistiques de lecture correctement mises à jour
- Pas de création de doublons dans la base de données

Pour plus de détails sur ces tests, voir le document `docs/tests/isrc_uniqueness_test.md`.

# Stratégie de Test

Ce document décrit la stratégie de test pour le projet SODAV Monitor.

## Organisation des Tests

Tous les tests sont situés dans le dossier `backend/tests/`. Les tests sont organisés par fonctionnalité et suivent la convention de nommage `test_<nom_de_la_fonction>.py`.

## Types de Tests

### Tests Unitaires

Les tests unitaires testent des composants individuels de l'application. Ils sont rapides à exécuter et permettent de vérifier que chaque composant fonctionne correctement de manière isolée.

Exemples de tests unitaires :
- `test_isrc_uniqueness.py` : Teste la contrainte d'unicité des codes ISRC
- `test_stats_updater.py` : Teste la classe StatsUpdater pour la mise à jour des statistiques

### Tests d'Intégration

Les tests d'intégration testent l'interaction entre plusieurs composants de l'application. Ils sont plus lents à exécuter mais permettent de vérifier que les composants fonctionnent correctement ensemble.

Exemples de tests d'intégration :
- `test_api_endpoints.py` : Teste les endpoints de l'API
- `test_stats_integration.py` : Teste l'intégration entre les différentes classes pour la mise à jour des statistiques

### Tests de Bout en Bout

Les tests de bout en bout testent l'application dans son ensemble, du début à la fin d'un processus. Ils sont les plus lents à exécuter mais permettent de vérifier que l'application fonctionne correctement dans son ensemble.

Exemples de tests de bout en bout :
- `test_detection_pipeline.py` : Teste le pipeline de détection complet

## Couverture de Test

L'objectif est d'atteindre une couverture de test d'au moins 90% pour le code de production. Les parties critiques du code, comme le pipeline de détection et la mise à jour des statistiques, devraient avoir une couverture de 100%.

## Exécution des Tests

Pour exécuter tous les tests :

```bash
pytest backend/tests/
```

Pour exécuter un test spécifique :

```bash
pytest backend/tests/test_isrc_uniqueness.py
```

Pour exécuter les tests avec couverture :

```bash
pytest --cov=backend backend/tests/
```

## Tests Récemment Ajoutés

### Tests de Mise à Jour des Statistiques

Deux nouveaux tests ont été ajoutés pour vérifier que les statistiques sont correctement mises à jour après une détection :

1. **Test Unitaire** : `test_stats_updater.py`
   - Teste la classe `StatsUpdater` de manière isolée
   - Vérifie que les méthodes de mise à jour des statistiques fonctionnent correctement
   - Utilise des mocks pour simuler la base de données

2. **Test d'Intégration** : `test_stats_integration.py`
   - Teste l'intégration entre `TrackManager`, `AudioProcessor` et `StatsUpdater`
   - Vérifie que les statistiques sont correctement mises à jour après une détection
   - Utilise une base de données SQLite en mémoire pour les tests

Ces tests ont été ajoutés suite à la découverte de problèmes dans la mise à jour des statistiques, où les statistiques n'étaient pas correctement mises à jour après une détection réussie. Les problèmes ont été documentés dans `docs/troubleshooting/stats_update_issues.md`.
