# Tests du Backend SODAV Monitor

## Vue d'ensemble
Ce document détaille la stratégie de tests et leur implémentation pour le backend du projet SODAV Monitor.

## État Actuel (Mars 2024)

### Modules à Haute Couverture (>90%)
- Authentication Module (95%)
  - Password verification
  - Token management
  - User validation
- WebSocket Communication (92%)
  - Connection handling
  - Message broadcasting
  - Error recovery
- Feature Extractor (92%)
  - Audio analysis
  - Music detection
  - Real-world sample testing
  - Performance benchmarking
- Audio Analyzer (94%)
  - Audio processing and feature extraction
  - Music/speech classification
  - Real-time processing capabilities
  - Concurrent processing support
  - Edge case handling
  - Performance optimization
- Stream Handler (94%)
  - Real-time audio processing
  - Buffer management
  - Error recovery
  - Performance optimization
  - Memory usage monitoring
  - Concurrent processing

### Modules en Cours d'Amélioration
- Analytics Manager (80%)
  - Data aggregation
  - Report generation
  - Performance optimization

### Modules en Cours de Test
#### Audio Analysis Module (85%)
- ✅ Process Audio
  - Mono/stereo handling
  - Sample rate conversion
  - Normalization
- ⚠️ Feature Extraction
  - Array vs scalar return types need standardization
  - Spectral features computation
  - Beat detection
- ⚠️ Music Detection
  - Threshold tuning
  - Speech vs music discrimination
  - Silence handling
- ✅ Error Handling
  - Empty audio data
  - Invalid formats
  - Edge cases

### Problèmes Connus
1. **Feature Type Consistency**
   - Spectral centroid returns array instead of float
   - Onset strength needs array return type
   - Zero crossing rate comparison needs array handling

2. **Error Messages**
   - Inconsistent error messages for empty audio data
   - Need standardization between "Empty audio data provided" and "No valid audio samples found"

3. **Edge Cases**
   - Very short audio samples handling needs improvement
   - Silence detection thresholds need adjustment
   - Memory usage optimization for large files

## Plan d'Action
1. Standardiser les types de retour des features
2. Unifier les messages d'erreur
3. Améliorer la gestion des cas limites
4. Optimiser la performance pour les fichiers volumineux

## Tests Implémentés

### Feature Extractor
1. **Initialisation et Configuration**
   - Test des paramètres par défaut
   - Validation des paramètres personnalisés
   - Gestion des paramètres invalides

2. **Extraction des Caractéristiques**
   - Validation des formes de sortie
   - Traitement audio stéréo
   - Gestion des entrées invalides

3. **Détection Musicale**
   - Classification musique vs. parole
   - Traitement du bruit
   - Cas limites et edge cases

4. **Tests de Performance**
   - Benchmarks d'extraction
   - Tests de mémoire
   - Traitement concurrent
   - Gestion des fichiers volumineux

5. **Tests avec Échantillons Réels**
   - Musique classique
   - Rock/Guitare
   - Voix parlée
   - Contenu mixte

### Stream Handler
1. **Gestion du Buffer**
   - Test des opérations de buffer
   - Validation de la taille du buffer
   - Gestion du débordement
   - Tests de performance

2. **Traitement en Temps Réel**
   - Tests de latence
   - Gestion de la backpressure
   - Tests de performance
   - Tests de concurrence

3. **Récupération d'Erreurs**
   - Tests de récupération automatique
   - Gestion des erreurs critiques
   - Tests de réinitialisation
   - Validation de l'intégrité des données

4. **Tests de Performance**
   - Benchmarks de latence
   - Tests de stabilité mémoire
   - Tests de traitement concurrent
   - Tests de charge

5. **Tests avec Données Réelles**
   - Flux audio en direct
   - Scénarios de réseau instable
   - Tests de débit variable
   - Validation des résultats

### Prochaines Étapes
1. **Stream Handler**
   - Améliorer la couverture des tests de buffer
   - Ajouter des tests de performance en temps réel
   - Implémenter des tests de récupération d'erreurs

2. **Analytics Manager**
   - Développer des tests d'agrégation de données
   - Ajouter des tests de génération de rapports
   - Implémenter des tests de performance

3. **Tests d'Intégration**
   - Tester le pipeline complet de détection
   - Valider le flux de données analytics
   - Vérifier la génération des rapports

## Métriques de Couverture
- Feature Extractor: 92% ✅
- Authentication: 95% ✅
- WebSocket: 92% ✅
- Stream Handler: 94% ✅
- Analytics Manager: 80% 🔄

## Exécution des Tests
```bash
# Tests unitaires
pytest tests/feature_extractor/test_feature_extractor.py -v
pytest tests/auth/test_auth.py -v
pytest tests/websocket/test_websocket.py -v

# Tests avec couverture
pytest --cov=backend tests/ --cov-report=html

# Tests de performance
pytest tests/feature_extractor/test_feature_extractor.py -v -m benchmark
```

## Testing Structure

### Component-Based Testing
Each major component has its own test directory with dedicated fixtures and test files:

```
backend/tests/
├── detection/
│   ├── audio_processor/
│   │   ├── test_core.py
│   │   ├── test_feature_extractor.py
│   │   ├── test_stream_handler.py
│   │   └── test_performance.py
│   ├── external/
│   │   ├── test_musicbrainz_recognizer.py
│   │   └── test_external_services.py
│   └── conftest.py
├── utils/
│   ├── test_auth.py
│   ├── test_stream_checker.py
│   ├── test_websocket.py
│   └── conftest.py
└── conftest.py
```

### Test Categories

#### 1. Unit Tests
- Feature Extractor (91% coverage)
  - Audio feature extraction
  - Music detection algorithms
  - Performance benchmarks
  - Memory usage monitoring

- Stream Handler (85% coverage)
  - Buffer management
  - Stream processing
  - Error handling
  - Performance metrics

#### 2. Integration Tests
- External Services
  - MusicBrainz integration
  - AcoustID API
  - Audd API
  - Error recovery

- WebSocket Communication
  - Connection management
  - Message broadcasting
  - Error handling
  - Redis integration

#### 3. Performance Tests
- Processing Latency
  - Audio chunk processing < 100ms
  - Stream buffer operations
  - Feature extraction timing

- Memory Usage
  - Buffer allocation < 50MB
  - Feature extraction < 100MB
  - Overall system < 500MB

### Running Tests

```bash
# Run all tests
PYTHONPATH=. pytest tests/ -v

# Run specific component tests
PYTHONPATH=. pytest tests/detection/audio_processor/test_feature_extractor.py -v
PYTHONPATH=. pytest tests/detection/audio_processor/test_stream_handler.py -v

# Run with coverage
PYTHONPATH=. pytest --cov=backend --cov-report=html

# Run performance tests
PYTHONPATH=. pytest tests/detection/audio_processor/test_performance.py -v
```

### Test Configuration
- pytest.ini settings
- Async test support
- Benchmark configuration
- Coverage requirements

### Current Status
1. ✅ Feature Extractor Tests
   - Complete test coverage
   - Performance benchmarks
   - Memory usage monitoring

2. ✅ Stream Handler Tests
   - Buffer management
   - Error handling
   - Performance metrics

3. 🔄 External Services Tests
   - MusicBrainz integration
   - API error handling
   - Rate limiting

4. 📝 Next Steps
   - Complete analytics tests
   - Add WebSocket stress tests
   - Improve error recovery tests
   - Add end-to-end tests

### Test Rules
1. Each component must have:
   - Unit tests
   - Integration tests (if applicable)
   - Performance benchmarks
   - Error handling tests

2. Coverage Requirements:
   - Core components: > 90%
   - Utils: > 85%
   - External integrations: > 80%

3. Performance Thresholds:
   - Processing latency < 100ms
   - Memory usage < 50MB per component
   - API response time < 2s

4. Error Handling:
   - All error paths tested
   - Recovery mechanisms verified
   - Edge cases covered

### Maintenance
- Regular test updates
- Performance monitoring
- Coverage reports
- Documentation updates

## Structure des Tests

```
backend/tests/
├── analytics/              # Tests des fonctionnalités analytiques
│   ├── test_stats.py
│   └── test_trends.py
├── detection/             # Tests du module de détection
│   ├── audio_processor/
│   │   ├── test_core.py
│   │   ├── test_stream_handler.py
│   │   ├── test_feature_extractor.py
│   │   └── test_track_manager.py
│   └── test_detection.py
├── utils/               # Tests des utilitaires
│   ├── test_auth.py
│   ├── test_redis_config.py
│   └── test_stream_checker.py
└── conftest.py         # Fixtures partagées
```

## Exécution des Tests

### Tests Unitaires
```bash
# Tous les tests
python -m pytest backend/tests/

# Tests spécifiques
python -m pytest backend/tests/detection/audio_processor/test_feature_extractor.py
```

### Tests avec Couverture
```bash
python -m pytest --cov=backend --cov-report=html
```

### Tests de Performance
```bash
# Exécuter les benchmarks
python -m pytest --benchmark-only

# Générer un rapport de benchmark
python -m pytest --benchmark-only --benchmark-json output.json
```

## Configuration

### Variables d'Environnement
```bash
TEST_DATABASE_URL=sqlite:///./test.db
TEST_REDIS_URL=redis://localhost:6379/1
TEST_API_KEY=test_key
ACOUSTID_API_KEY=test_acoustid_key
AUDD_API_KEY=test_audd_key
```

### Dépendances de Test
```
pytest==8.3.4
pytest-asyncio==0.24.0
pytest-cov==5.0.0
pytest-mock==3.14.0
pytest-redis==3.1.2
pytest-benchmark==4.0.0
```

## Critères de Performance

### Temps de Réponse
- Traitement audio : < 1s par échantillon
- Détection de piste : < 3s par piste
- API REST : < 100ms par requête
- WebSocket : < 50ms par message

### Utilisation des Ressources
- CPU : < 80% en charge normale
- Mémoire : < 1GB par processus
- Disque : < 100MB/s en écriture
- Redis : < 1000 opérations/s

### Concurrence
- Flux simultanés : > 50 stations
- Connexions WebSocket : > 1000
- Requêtes API : > 1000 req/s

## Maintenance

### Mise à Jour des Tests
- Revue régulière des tests
- Mise à jour des mocks
- Nettoyage des tests obsolètes
- Documentation à jour

### Intégration Continue
- Exécution automatique des tests
- Vérification de la couverture
- Rapports de test
- Notifications d'échec
- Benchmarks automatisés

## Structure des Tests (Mise à jour Mars 2024)

```
backend/tests/
├── analytics/              # Tests des fonctionnalités analytiques
│   ├── test_stats.py
│   └── test_trends.py
├── detection/             # Tests du module de détection
│   ├── test_audio_processor/
│   │   ├── test_core.py
│   │   ├── test_stream_handler.py
│   │   ├── test_feature_extractor.py
│   │   ├── test_track_manager.py
│   │   └── test_external_services.py
│   └── test_detection.py
├── reports/              # Tests de génération de rapports
│   └── test_generator.py
├── utils/               # Tests des utilitaires
│   ├── test_auth.py
│   ├── test_redis_config.py
│   └── test_stream_checker.py
├── test_api.py         # Tests d'API consolidés
├── test_websocket.py   # Tests WebSocket
├── test_system.py      # Tests système
├── test_radio.py       # Tests radio
├── test_database.py    # Tests base de données
├── test_error_recovery.py  # Tests de récupération d'erreurs
├── test_performance.py    # Tests de performance [Nouveau]
└── conftest.py         # Fixtures partagées
```

## État Actuel de la Couverture (Mars 2024)

### Modules à Haute Couverture (>90%)
- Analytics Module (95%)
  - Génération de rapports
  - Calcul de statistiques
  - Analyse de tendances
- WebSocket Communication (92%)
  - Gestion des connexions
  - Diffusion des messages
  - Validation des données
- Services Externes (95%)
  - Intégration MusicBrainz
  - Intégration Audd
  - Gestion des erreurs et retries
- Gestion des Erreurs (95%)
  - Scénarios de récupération
  - Timeouts et retries
  - Gestion des ressources système
- Performance (90%) [Nouveau]
  - Tests de charge
  - Benchmarks
  - Profiling

### Modules à Couverture Moyenne (70-90%)
- Détection Audio (85%)
  - Traitement des flux
  - Extraction de caractéristiques
  - Gestion des pistes
- API REST (80%)
  - Endpoints principaux
  - Validation des requêtes
  - Gestion des erreurs

## Améliorations Récentes

### 1. Tests de Performance [Nouveau]
- Tests complets de performance
  - Traitement audio
  - Flux concurrents
  - Écriture en base de données
  - Utilisation mémoire
  - Utilisation CPU
  - Cache Redis
  - Diffusion WebSocket
  - Performance API
  - Pipeline de détection
  - Gestion de charge

### 2. Gestion des Erreurs
- Tests complets de récupération d'erreurs
  - Reconnexion des flux
  - Retry des détections
  - Gestion des verrous de base de données
  - Récupération des données audio invalides
  - Reconnexion Redis
  - Reconnexion WebSocket
  - Gestion des limites d'API
  - Gestion des ressources système

### 3. Services Externes
- Tests complets pour MusicBrainz et Audd
  - Détection réussie
  - Gestion des erreurs
  - Timeouts
  - Retries automatiques
  - Validation des réponses
  - Gestion des API keys invalides

## Prochaines Étapes

### Court Terme
1. Optimiser les tests existants
   - Réduire le temps d'exécution
   - Améliorer l'isolation
   - Nettoyer les ressources

2. Améliorer la documentation
   - Ajouter des exemples de cas d'utilisation
   - Documenter les scénarios de test
   - Mettre à jour les guides de contribution

3. Automatiser les tests de performance
   - Intégration continue
   - Alertes sur régression
   - Rapports de tendance

### Long Terme
1. Tests d'intégration complets
2. Tests de sécurité
3. Tests de régression automatisés
4. Tests de déploiement

## Bonnes Pratiques

### 1. Organisation des Tests
- Un fichier de test par module
- Nommage explicite des tests
- Isolation des tests
- Documentation claire

### 2. Mocking
- Utilisation de `unittest.mock`
- Fixtures réutilisables
- Simulation des services externes
- Gestion des états

### 3. Assertions
- Assertions claires et précises
- Validation des types
- Vérification des états
- Messages d'erreur explicites

### 4. Performance
- Tests rapides (<1s par test)
- Parallélisation possible
- Fixtures optimisées
- Cache approprié

## Exécution des Tests

### Tests Unitaires
```bash
python -m pytest backend/tests/
```

### Tests avec Couverture
```bash
python -m pytest --cov=backend --cov-report=html
```

### Tests Spécifiques
```bash
# Tests de détection
python -m pytest backend/tests/detection/

# Tests de récupération d'erreurs
python -m pytest backend/tests/test_error_recovery.py

# Tests de performance
python -m pytest backend/tests/test_performance.py -v --benchmark-only
```

### Tests de Performance
```bash
# Exécuter tous les benchmarks
python -m pytest --benchmark-only

# Générer un rapport de benchmark
python -m pytest --benchmark-only --benchmark-json output.json

# Comparer avec un benchmark précédent
python -m pytest-benchmark compare output.json
```

## Configuration

### Variables d'Environnement
```bash
TEST_DATABASE_URL=sqlite:///./test.db
TEST_REDIS_URL=redis://localhost:6379/1
TEST_API_KEY=test_key
ACOUSTID_API_KEY=test_acoustid_key
AUDD_API_KEY=test_audd_key
```

### Dépendances de Test
```
pytest==7.4.0
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.11.1
pytest-benchmark==4.0.0  # [Nouveau] Pour les tests de performance
aioresponses==0.7.4
psutil==5.9.0
numpy==1.21.0  # [Nouveau] Pour la génération de données audio
```

## Critères de Performance

### Temps de Réponse
- Traitement audio : < 1s par échantillon
- Détection de piste : < 3s par piste
- API REST : < 100ms par requête
- WebSocket : < 50ms par message

### Utilisation des Ressources
- CPU : < 80% en charge normale
- Mémoire : < 1GB par processus
- Disque : < 100MB/s en écriture
- Redis : < 1000 opérations/s

### Concurrence
- Flux simultanés : > 50 stations
- Connexions WebSocket : > 1000
- Requêtes API : > 1000 req/s

## Maintenance

### Mise à Jour des Tests
- Revue régulière des tests
- Mise à jour des mocks
- Nettoyage des tests obsolètes
- Documentation à jour

### Intégration Continue
- Exécution automatique des tests
- Vérification de la couverture
- Rapports de test
- Notifications d'échec
- Benchmarks automatisés [Nouveau]

## Conclusion
La suite de tests continue d'évoluer avec le projet. Les améliorations récentes, notamment l'ajout des tests de performance, de récupération d'erreurs et des services externes, ont permis d'augmenter significativement la couverture et la qualité des tests. Les prochaines étapes se concentreront sur l'optimisation des tests existants et l'automatisation des tests de performance.

## Module-Specific Test Documentation

### Detection Module Tests

#### Overview
The detection module is responsible for audio stream processing, music detection, and track identification. The test suite covers all aspects of the detection pipeline, from raw audio processing to external service integration.

#### Test Structure
```bash
backend/tests/detection/
├── audio_processor/           # Audio processing specific tests
├── test_external_services.py  # Tests for MusicBrainz and Audd integration
├── test_station_monitor.py    # Radio station monitoring tests
├── test_track_manager.py      # Track management and storage tests
├── test_stream_handler.py     # Audio stream handling tests
├── test_feature_extractor.py  # Audio feature extraction tests
├── test_track_detection.py    # End-to-end track detection tests
└── test_fingerprint.py        # Audio fingerprinting tests
```

#### Component Details

1. **Audio Feature Extraction** (`test_feature_extractor.py`)
   - Tests for spectral feature extraction
   - Frequency analysis validation
   - Audio segment processing
   - Feature vector generation
   - Performance benchmarks for feature extraction

2. **Stream Handler** (`test_stream_handler.py`)
   - Audio stream connection tests
   - Buffer management validation
   - Error recovery scenarios
   - Stream quality monitoring
   - Resource cleanup verification

3. **Track Manager** (`test_track_manager.py`)
   - Track metadata management
   - Database operations for tracks
   - Duplicate detection handling
   - Track history maintenance
   - Cache management tests

4. **Station Monitor** (`test_station_monitor.py`)
   - Station connection management
   - Stream health monitoring
   - Auto-recovery testing
   - Performance under load
   - Multi-station concurrent processing

5. **External Services** (`test_external_services.py`)
   - MusicBrainz API integration
   - Audd API integration
   - Error handling and retries
   - Rate limiting compliance
   - Response parsing and validation

6. **Track Detection** (`test_track_detection.py`)
   - End-to-end detection pipeline
   - Detection accuracy validation
   - Performance benchmarks
   - Edge case handling
   - Integration with all components

7. **Fingerprinting** (`test_fingerprint.py`)
   - Fingerprint generation
   - Fingerprint matching
   - Database storage and retrieval
   - Optimization tests
   - Accuracy validation

#### Running Detection Tests

```bash
# Run all detection tests
pytest backend/tests/detection/

# Run specific component tests
pytest backend/tests/detection/test_feature_extractor.py
pytest backend/tests/detection/test_track_detection.py

# Run with coverage report
pytest backend/tests/detection/ --cov=backend.detection --cov-report=html
```

#### Test Coverage Goals
- Feature Extraction: 95%
- Stream Handling: 90%
- Track Management: 95%
- Station Monitoring: 90%
- External Services: 95%
- Track Detection: 90%
- Fingerprinting: 95%

#### Common Test Scenarios

1. **Feature Extraction**
   - Valid audio input processing
   - Invalid audio handling
   - Resource management
   - Performance under load

2. **Stream Processing**
   - Connection establishment
   - Data buffering
   - Error handling
   - Resource cleanup

3. **Track Detection**
   - Successful detection flow
   - Failed detection handling
   - Multiple concurrent detections
   - Edge cases (silence, noise)

4. **External Services**
   - Successful API calls
   - Error handling
   - Rate limiting
   - Timeout handling

#### Mocking Strategy
- External API calls (MusicBrainz, Audd)
- Database connections
- File system operations
- Network streams
- Time-dependent operations

#### Performance Benchmarks
- Feature extraction speed
- Detection pipeline latency
- Memory usage under load
- Concurrent stream handling
- Database operation timing

### Audio Processing Tests

#### Overview
The audio processing module is responsible for analyzing audio streams, extracting features, and detecting music. The test suite covers all aspects of audio processing, from raw audio handling to feature extraction and music detection.

#### Test Structure
```bash
backend/tests/detection/audio_processor/
├── test_audio_analysis.py    # Audio analysis and feature extraction tests
├── test_external_services.py # MusicBrainz and Audd integration tests
├── test_local_detection.py   # Local database detection tests
└── test_recognition_core.py  # Core recognition flow tests
```

#### Component Details

1. **Audio Analysis** (`test_audio_analysis.py`)
   - Audio feature extraction validation
   - Music detection accuracy
   - Duration calculation
   - Sample rate handling
   - Audio format conversion
   - Error handling for invalid audio

2. **External Services** (`test_external_services.py`)
   - MusicBrainz API integration
   - Audd API integration
   - Error handling and retries
   - Rate limiting compliance
   - Response validation
   - Mock API responses

3. **Local Detection** (`test_local_detection.py`)
   - Fingerprint generation
   - Local database matching
   - Confidence scoring
   - Cache management
   - Database operations
   - Error handling

4. **Recognition Core** (`test_recognition_core.py`)
   - End-to-end recognition flow
   - Service initialization
   - Component integration
   - Error handling
   - Recognition accuracy
   - Performance benchmarks

#### Running Audio Processing Tests

```bash
# Run all audio processing tests
pytest backend/tests/detection/audio_processor/

# Run specific component tests
pytest backend/tests/detection/audio_processor/test_audio_analysis.py
pytest backend/tests/detection/audio_processor/test_external_services.py

# Run with coverage report
pytest backend/tests/detection/audio_processor/ --cov=backend.detection.audio_processor --cov-report=html
```

#### Test Coverage Goals
- Audio Analysis: 95%
- External Services: 95%
- Local Detection: 90%
- Recognition Core: 90%

#### Common Test Scenarios

1. **Audio Analysis**
   - Feature extraction from various audio formats
   - Music vs. speech detection
   - Duration calculation accuracy
   - Sample rate conversion
   - Error handling for corrupted audio

2. **External Services**
   - Successful API responses
   - Error responses
   - Rate limiting
   - Network timeouts
   - Invalid API keys
   - Malformed responses

3. **Local Detection**
   - Successful fingerprint matches
   - Near-matches with confidence scoring
   - No matches found
   - Database errors
   - Cache hits and misses

4. **Recognition Core**
   - Full recognition pipeline
   - Service fallback behavior
   - Error propagation
   - Performance under load
   - Memory usage

#### Mocking Strategy
- External API calls (MusicBrainz, Audd)
- Audio file operations
- Database operations
- Cache operations
- Time-dependent operations

#### Performance Benchmarks
- Feature extraction speed
- Recognition pipeline latency
- Memory usage under load
- Database operation timing
- API response handling

### Audio Processor Performance Tests

#### Overview
The audio processor performance tests validate the efficiency and resource usage of the audio processing pipeline. These tests ensure that the system can handle real-world workloads while maintaining acceptable performance characteristics.

#### Test Structure
```bash
backend/tests/detection/audio_processor/
└── test_audio_processor_performance.py  # Performance benchmarks for audio processing
```

#### Component Details

1. **Process Stream Performance** (`test_process_stream_performance`)
   - Benchmarks audio stream processing speed
   - Tests with large audio samples (10 seconds)
   - Validates output tuple structure
   - Measures processing latency

2. **Feature Extraction Performance** (`test_feature_extraction_performance`)
   - Benchmarks feature extraction speed
   - Tests with complex audio signals
   - Validates feature vector dimensions
   - Measures extraction time

3. **Fingerprint Matching Performance** (`test_fingerprint_matching_performance`)
   - Benchmarks matching against large database (1000 fingerprints)
   - Tests matching speed and accuracy
   - Validates result consistency
   - Measures lookup time

4. **End-to-End Performance** (`test_end_to_end_performance`)
   - Tests complete audio processing pipeline
   - Measures total processing time
   - Validates system integration
   - Tests with real-world scenarios

5. **Memory Usage** (`test_memory_usage`)
   - Monitors memory consumption
   - Tracks memory growth
   - Validates resource cleanup
   - Ensures memory stability

#### Running Performance Tests

```bash
# Run all performance tests
pytest backend/tests/detection/audio_processor/test_audio_processor_performance.py -v

# Run specific benchmark
pytest backend/tests/detection/audio_processor/test_audio_processor_performance.py -v -k "test_process_stream_performance"

# Generate benchmark report
pytest backend/tests/detection/audio_processor/test_audio_processor_performance.py --benchmark-only --benchmark-json output.json
```

#### Performance Targets

1. **Stream Processing**
   - Processing time: < 1s per 10-second audio sample
   - Memory usage: < 100MB per stream
   - CPU usage: < 50% single core

2. **Feature Extraction**
   - Extraction time: < 500ms per sample
   - Memory usage: < 50MB per extraction
   - Feature vector generation: < 200ms

3. **Fingerprint Matching**
   - Lookup time: < 100ms per query
   - Database size: Up to 1000 fingerprints
   - Match accuracy: > 95%

4. **End-to-End Pipeline**
   - Total processing time: < 3s per sample
   - Memory usage: < 200MB total
   - Success rate: > 99%

#### Benchmark Configuration

```python
@pytest.mark.benchmark(
    group="audio_processor",
    min_rounds=100,
    max_time=2.0
)
```

- `group`: Organizes related benchmarks
- `min_rounds`: Minimum number of iterations
- `max_time`: Maximum time per benchmark
- `warmup`: False (disabled for consistent results)

#### Dependencies
```
pytest-benchmark==4.0.0  # Performance testing
psutil==5.9.0           # System resource monitoring
numpy==1.21.0           # Audio data generation
```

## Audio Feature Extraction Tests

### Overview
The `FeatureExtractor` test suite provides comprehensive testing for audio feature extraction and music detection functionality. Located in `backend/tests/detection/audio_processor/test_feature_extractor.py`, these tests ensure robust and accurate audio analysis.

### Test Structure
1. **Initialization Tests** (`TestFeatureExtractorInitialization`):
   - Default parameter validation
   - Custom parameter configuration
   - Invalid parameter handling
   - Configuration persistence

2. **Feature Extraction Tests** (`TestFeatureExtraction`):
   - Feature shape validation
   - Stereo audio handling
   - Input validation
   - Feature completeness checks
   - Output format verification

3. **Music Detection Tests** (`TestMusicDetection`):
   - Detection accuracy
   - Confidence score validation
   - Missing feature handling
   - Invalid input management
   - Edge case processing

4. **Audio Duration Tests** (`TestAudioDuration`):
   - Duration calculation accuracy
   - Stereo file handling
   - Input validation
   - Edge case management

5. **Performance Tests** (`TestFeatureExtractorPerformance`):
   - Feature extraction benchmarks
   - Music detection speed
   - Memory usage monitoring
   - Processing efficiency

### Running Tests
```bash
# Run all feature extractor tests
python -m pytest tests/detection/audio_processor/test_feature_extractor.py -v

# Run only performance tests
python -m pytest tests/detection/audio_processor/test_feature_extractor.py -v -m benchmark

# Run with coverage
python -m pytest tests/detection/audio_processor/test_feature_extractor.py --cov=detection.audio_processor.feature_extractor
```

### Performance Targets
- Feature extraction: < 100ms for 1s audio
- Music detection: < 10ms per decision
- Memory usage: < 100MB peak
- Overall latency: < 200ms end-to-end

### Dependencies
- pytest
- pytest-benchmark
- numpy
- librosa

### Test Data
- Synthetic test signals (sine waves, noise)
- Sample audio files
- Edge case inputs
- Invalid data samples

### Tests Récemment Améliorés
#### Stream Handler (Mars 2024)
- **Real-Time Processing**
  - Improved buffer overflow handling
  - Added backpressure testing
  - Enhanced concurrent processing tests
  - Implemented memory usage monitoring

- **Error Recovery**
  - Added automatic reset after critical errors
  - Improved error recovery scenarios
  - Enhanced data integrity validation
  - Added network interruption handling

- **Performance**
  - Added processing latency benchmarks
  - Implemented memory stability tests
  - Enhanced concurrent processing tests
  - Added buffer optimization metrics

- **Integration**
  - Added tests with audio processors
  - Improved stream health monitoring
  - Enhanced metadata handling tests
  - Added real-world audio sample tests

#### Audio Analyzer (Mars 2024)
1. **Tests de Performance**
   - Latence de traitement audio
   - Latence d'extraction de caractéristiques
   - Utilisation de la mémoire
   - Benchmarks de performance

2. **Tests de Traitement Concurrent**
   - Extraction parallèle de caractéristiques
   - Détection musicale simultanée
   - Gestion des ressources en parallèle

3. **Tests de Cas Limites**
   - Audio très court (10ms)
   - Détection de silence
   - Valeurs extrêmes d'amplitude
   - Gestion des erreurs améliorée

4. **Tests de Robustesse**
   - Différents taux d'échantillonnage
   - Audio complexe multi-instruments
   - Conditions de charge élevée