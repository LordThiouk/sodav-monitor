# Tests du Backend SODAV Monitor

## Vue d'ensemble
Ce document détaille la stratégie de tests et leur implémentation pour le backend du projet SODAV Monitor.

## Configuration des Tests

### Prérequis
- Python 3.8+
- pytest
- pytest-asyncio
- pytest-cov
- pytest-mock
- pytest-redis
- aiohttp
- aioresponses
- numpy
- librosa
- soundfile

### Variables d'Environnement Requises
Pour exécuter les tests, les variables d'environnement suivantes doivent être configurées :

```bash
# Base de données
TEST_DATABASE_URL=sqlite:///./test.db

# JWT
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=test_jwt_secret

# APIs externes
ACOUSTID_API_KEY=test_acoustid_key
AUDD_API_KEY=test_audd_key

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1

# Python Path
PYTHONPATH=.
```

## Structure des Tests

Les tests sont organisés dans le dossier `backend/tests/` selon la structure suivante :

```
backend/tests/
├── analytics/
│   ├── test_generate_detections.py
│   └── test_stats_manager.py
├── detection/
│   ├── test_audio_processor/
│   │   ├── test_feature_extractor.py
│   │   ├── test_stream_handler.py
│   │   ├── test_track_manager.py
│   │   └── test_station_monitor.py
│   └── test_core.py
├── reports/
│   └── test_generator.py
├── utils/
│   ├── test_auth.py
│   ├── test_redis_config.py
│   └── test_stream_checker.py
└── conftest.py
```

## Composants Testés

### 1. Processeur Audio (`test_audio_processor/`)
- **Feature Extractor** (`test_feature_extractor.py`)
  - Extraction des caractéristiques audio
  - Détection musique/parole
  - Gestion des erreurs d'analyse
  - Performance et utilisation mémoire

- **Stream Handler** (`test_stream_handler.py`)
  - Gestion des flux audio
  - Téléchargement et compression
  - Vérification des statuts
  - Gestion des erreurs réseau

- **Track Manager** (`test_track_manager.py`)
  - Détection des pistes
  - Gestion des correspondances
  - Mise à jour des statistiques
  - Gestion des erreurs de base de données

- **Station Monitor** (`test_station_monitor.py`)
  - Monitoring des stations
  - Gestion de la santé
  - Reconnexion automatique
  - Gestion des erreurs

### 2. Authentification (`test_auth.py`)
- Vérification des mots de passe
- Génération et validation des tokens JWT
- Gestion des sessions utilisateur

### 3. Vérification des Flux (`test_stream_checker.py`)
- Vérification de la disponibilité des flux
- Gestion des timeouts et erreurs réseau
- Validation des métadonnées des flux

### 4. Configuration Redis (`test_redis_config.py`)
- Tests de connexion
- Gestion des erreurs de connexion
- Configuration du pub/sub

### 5. Génération de Rapports (`test_generator.py`)
- Génération de rapports de détection
- Génération de rapports de stations
- Validation des dates et filtres
- Gestion des données vides

### 6. Génération de Détections (`test_generate_detections.py`)
- Génération de détections pour les pistes
- Gestion des stations actives
- Mise à jour des statistiques
- Gestion des erreurs de base de données

## Journal des Modifications

### 2024-03-30
- Implémentation complète des tests du module audio_processor :
  - Tests du Feature Extractor :
    - Extraction des caractéristiques audio
    - Détection musique/parole
    - Gestion des erreurs
    - Tests de performance et mémoire
  - Tests du Stream Handler :
    - Gestion des flux audio
    - Compression et traitement
    - Vérification des statuts
  - Tests du Track Manager :
    - Détection et correspondance
    - Gestion des statistiques
    - Gestion des erreurs
  - Tests du Station Monitor :
    - Monitoring des stations
    - Gestion de la santé
    - Tests de reconnexion
  - Couverture de code > 90% pour le module

### 2024-03-29
- Amélioration des tests du module de génération de rapports :
  - Tests de création de rapports de test
  - Tests de gestion des états des rapports
  - Tests de gestion des erreurs de base de données
  - Tests de gestion des erreurs de fichiers
  - Couverture de 98% pour le module `generate_test_report.py`

## Bonnes Pratiques

1. **Isolation des Tests**
   - Utilisation de fixtures pour la configuration
   - Nettoyage après chaque test
   - Pas de dépendances entre les tests

2. **Mocking**
   - Mock des appels API externes
   - Mock des sessions de base de données
   - Mock des connexions Redis

3. **Assertions**
   - Vérification des valeurs de retour
   - Vérification des appels de méthodes
   - Vérification des mises à jour de données

4. **Gestion des Erreurs**
   - Test des cas d'erreur
   - Vérification des messages d'erreur
   - Test des mécanismes de fallback

## Exécution des Tests

Pour exécuter tous les tests :
```bash
python -m pytest
```

Pour exécuter un module spécifique :
```bash
python -m pytest backend/tests/path/to/test_file.py
```

Pour générer un rapport de couverture :
```bash
python -m pytest --cov=backend --cov-report=html
```

## Objectifs de Couverture

### Cibles
- Couverture globale : > 80%
- Modules critiques : > 90%
  - Détection audio
  - Gestion des flux
  - Authentification
  - Rapports
  - Analytics

### Métriques
- Lignes de code
- Branches
- Fonctions
- Complexité cyclomatique

## Automatisation

### Scripts
- `run_tests.py` : Exécution des tests
  - Vérification des dépendances
  - Linting du code
  - Exécution des tests
  - Génération des rapports

### Intégration Continue
- Exécution automatique des tests
- Vérification de la couverture
- Validation du code

## Prochaines Étapes

### Court Terme
1. Améliorer la couverture de code des nouveaux modules
2. Optimiser les performances des tests
3. Ajouter des tests de stress pour WebSocket

### Long Terme
1. Tests de charge
2. Tests de sécurité
3. Tests de régression
4. Automatisation complète

## Stratégie de Mock
- Utilisation de `unittest.mock.patch` avec `autospec=True`
- Mock des fonctions librosa pour tests reproductibles
- Simulation de signaux audio synthétiques
- Gestion appropriée des cas d'erreur 

### Couverture des Tests

La couverture actuelle des tests est de 87% pour le module d'analyse audio, avec des points clés :
- Couverture complète des fonctionnalités de base
- Tests robustes pour la détection de musique
- Gestion appropriée des cas d'erreur
- Mocking efficace des dépendances externes

### Bonnes Pratiques

1. **Isolation des Tests**
   - Utilisation de fixtures pour la configuration
   - Mocking des dépendances externes
   - Tests indépendants et atomiques

2. **Gestion des Erreurs**
   - Tests explicites des cas d'erreur
   - Vérification des limites et cas particuliers
   - Documentation des comportements attendus

3. **Performance**
   - Tests optimisés pour l'exécution rapide
   - Utilisation appropriée des mocks
   - Minimisation des dépendances externes

4. **Maintenance**
   - Tests bien documentés
   - Structure claire et organisée
   - Nommage explicite des tests 

# SODAV Monitor Test Documentation

## Test Status

### Current Coverage: 10%
The test suite currently covers core functionality with room for improvement in utility modules.

## Test Structure

### Validators Module (`tests/utils/test_validators.py`)
- **Email Validation Tests**
  - Standard email formats
  - Special characters in local part
  - Domain validation
  - Edge cases (whitespace, dots, length)
- **Date Range Validation Tests**
  - Valid date ranges
  - Invalid date ranges
  - Edge cases (same date, far future/past)
- **Report Format Validation Tests**
  - Valid formats (CSV, XLSX, PDF)
  - Invalid format handling
- **Subscription Frequency Tests**
  - Valid frequencies (Daily, Weekly, Monthly)
  - Invalid frequency handling

### Analytics Module (`tests/analytics/test_analytics.py`)
- **Track Statistics Tests**
  - `test_update_detection_stats_new_track`: Validates new track detection statistics
  - `test_update_detection_stats_existing_track`: Verifies updates to existing track stats
  - `test_update_detection_stats_error`: Tests error handling in stats updates
  - Fields tested:
    - Detection count
    - Total play time
    - Average confidence
    - Last detection timestamp

- **Artist Statistics Tests**
  - Artist track aggregation
  - Detection metrics across all artist tracks
  - Play time calculation per artist
  - Last detection tracking

- **Station Track Statistics Tests**
  - Play count per station
  - Station-specific confidence metrics
  - Station play time tracking
  - Last played timestamp updates

- **Report Generation Tests**
  - `test_generate_daily_report`: Tests daily report generation
    - Total detections
    - Total play time
    - Top tracks and artists
  - Station statistics
  - `test_generate_daily_report_error`: Validates error handling

- **Trend Analysis Tests**
  - `test_get_trend_analysis`: Tests trend analysis over periods
    - Track trends
    - Artist trends
    - Period calculations
  - `test_get_trend_analysis_error`: Verifies error handling

- **Batch Update Tests**
  - `test_update_all_stats`: Tests bulk statistics updates
  - `test_error_handling`: Comprehensive error scenario testing

### Current Coverage Status (as of 2024-03-26)

#### High Coverage Areas (>90%)
- Analytics Module (100%)
  - Stats Manager
  - Report Generation
  - Trend Analysis
  - Error Handling
- WebSocket Communication (81%)
  - Connection Management
  - Message Broadcasting
  - Error Handling
  - Data Validation

### Medium Coverage Areas (70-90%)
- Audio Detection
- WebSocket Communication
- Station Management

#### Areas Needing Improvement (<70%)
- External Service Integration
- Error Recovery Scenarios
- Performance Testing

### Recent Improvements
1. **Redis Configuration Tests**
   - Added comprehensive connection testing
   - Improved error handling coverage
   - Added password authentication tests
   - Implemented cleanup utilities

2. **Test Organization**
   - Consolidated API tests
   - Improved test isolation
   - Enhanced mock implementations
   - Better error simulation

3. **Documentation**
   - Updated test coverage metrics
   - Added new test categories
   - Improved setup instructions
   - Enhanced troubleshooting guide 

### Recent Test Improvements
1. **Analytics Testing**
   - Added comprehensive stats update tests
   - Implemented report generation validation
   - Enhanced trend analysis coverage
   - Added error handling scenarios
   - Improved data validation
2. **WebSocket Testing**
   - Added reconnection scenario tests
   - Implemented failed connection handling
   - Enhanced message validation
   - Added maximum connection limit tests
   - Improved error handling coverage
   - Added data validation for track detection
   - Implemented connection cleanup
   - Added comprehensive error scenarios 

## Modules de Test

### 1. WebSocket (`test_websocket.py`)
Tests pour la gestion des connexions WebSocket en temps réel.

#### Tests de Connexion
- `test_connection_manager_connect`: Établissement de connexion
- `test_connection_manager_disconnect`: Déconnexion
- `test_connection_manager_max_connections`: Limite de connexions

#### Tests de Diffusion
- `test_connection_manager_broadcast`: Diffusion de messages
- `test_connection_manager_broadcast_with_failed_connection`: Gestion des échecs
- `test_send_heartbeat`: Envoi de heartbeats

#### Tests de Messages
- `test_process_websocket_message_heartbeat`: Traitement des heartbeats
- `test_process_websocket_message_invalid_json`: Messages JSON invalides
- `test_process_websocket_message_unknown_type`: Types de messages inconnus
- `test_process_websocket_message_validation`: Validation des messages

#### Tests d'Intégration Redis
- `test_redis_integration`: Intégration avec Redis pour la diffusion

### 2. Redis Configuration (`test_redis_config.py`)
Tests pour la configuration et la gestion de Redis.

#### Tests de Configuration
- `test_get_redis_success`: Création réussie du client
- `test_get_redis_with_password`: Authentification avec mot de passe
- `test_get_redis_connection_error`: Gestion des erreurs de connexion
- `test_get_redis_invalid_settings`: Paramètres invalides
- `test_get_redis_timeout`: Timeouts de connexion

#### Tests de Connexion
- `test_check_redis_connection_success`: Vérification de connexion réussie
- `test_check_redis_connection_failure`: Échec de connexion
- `test_check_redis_connection_no_client`: Absence de client

#### Tests Pub/Sub
- `test_redis_pubsub`: Fonctionnalité pub/sub
- `test_redis_connection_pool`: Configuration du pool de connexions
- `test_redis_ssl_config`: Configuration SSL
- `test_redis_max_connections`: Limite de connexions

### 3. Stream Checker (`test_stream_checker.py`)
Tests pour la vérification des flux radio.

#### Tests de Disponibilité
- `test_check_stream_availability_success`: Vérification réussie
- `test_check_stream_availability_not_audio`: Contenu non-audio
- `test_check_stream_availability_timeout`: Timeouts
- `test_check_stream_availability_error`: Erreurs client

#### Tests de Métadonnées
- `test_get_stream_metadata_success`: Récupération réussie
- `test_get_stream_metadata_no_metadata`: Absence de métadonnées
- `test_get_stream_metadata_timeout`: Timeouts
- `test_get_stream_metadata_error`: Erreurs client

### 4. Track Detection (`test_track_detection.py`)
Tests pour la détection des morceaux.

#### Tests de Détection
- `test_detect_music_vs_speech`: Différenciation musique/parole
- `test_local_detection_success`: Détection locale
- `test_musicbrainz_fallback`: Fallback MusicBrainz
- `test_audd_fallback`: Fallback Audd
- `test_all_detection_methods_fail`: Échec de toutes les méthodes

#### Tests de Confiance
- `test_low_confidence_results`: Résultats peu fiables
- `test_feature_extraction`: Extraction de caractéristiques

#### Tests d'Erreur
- `test_error_handling`: Gestion des erreurs
- `test_detection_with_missing_api_keys`: Clés API manquantes

### Mocking HTTP avec aioresponses
```python
@pytest.mark.asyncio
async def test_check_stream_availability(mock_aioresponse):
    """Test stream availability check with mocked HTTP responses."""
    url = "http://test.stream"
    mock_aioresponse.head(url, status=200, headers={'content-type': 'audio/mpeg'})
    
    result = await check_stream_availability(url)
    assert result['is_available'] is True
    assert result['is_audio_stream'] is True
```

### Tests de Métadonnées de Flux
```python
@pytest.mark.asyncio
async def test_get_stream_metadata(mock_aioresponse):
    """Test stream metadata retrieval with mocked response."""
    url = "http://test.stream"
    mock_aioresponse.get(url, status=200, headers={
        'icy-name': 'Test Radio',
        'icy-genre': 'Test Genre',
        'icy-br': '128'
    })
    
    result = await get_stream_metadata(url)
    assert result == {
        'name': 'Test Radio',
        'genre': 'Test Genre',
        'bitrate': '128'
    }
```

### Tests d'Authentification avec Datetime Mock
```python
@patch('backend.utils.auth.datetime')
def test_create_access_token(mock_datetime):
    """Test token creation with mocked datetime."""
    fixed_time = datetime(2025, 1, 1, 12, 0)
    mock_datetime.now.return_value = fixed_time
    
    data = {"sub": "test@example.com"}
    token = create_access_token(data)
    
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    expected_exp = int(fixed_time.timestamp()) + 15 * 60
    assert payload["exp"] == expected_exp
```

## Prochaines Priorités de Test

### 1. Module de Détection Audio (`detection/audio_processor/`)
- Tests pour `recognition_core.py`
  - Initialisation du reconnaisseur
  - Flux de reconnaissance principal
  - Gestion des seuils de confiance
  - Intégration avec MusicBrainz

- Tests pour `audio_analysis.py`
  - Extraction des caractéristiques audio
  - Traitement des données audio brutes
  - Validation des paramètres d'analyse

### 2. Module Frontend
- Tests des composants React :
  - `LiveMonitor.tsx`
  - `AnalyticsOverview.tsx`
  - `Dashboard.tsx`
- Tests d'intégration WebSocket
- Tests de gestion d'état
- Tests de rendu UI

### 3. Module de Gestion de Fichiers (`utils/file_manager.py`)
- Tests de création de chemins de rapports
- Tests de gestion des répertoires
- Tests de nommage de fichiers
- Tests de gestion des erreurs

## État Actuel de la Couverture

### Modules à Haute Couverture (>90%)
- `backend/analytics/generate_test_report.py`: 98%
- `backend/analytics/generate_detections.py`: En cours d'amélioration

### Modules à Couverture Moyenne (50-90%)
- `backend/utils/`: ~70%
- `backend/models/`: ~65%

### Modules Nécessitant des Tests (<50%)
- `backend/detection/audio_processor/`: ~20%
- `frontend/src/components/`: Non testé
- `backend/utils/file_manager.py`: Non testé

### Current Coverage Status (as of 2024-03-26)

#### High Coverage Areas (>90%)
- Analytics Module (100%)
  - Stats Manager
  - Report Generation
  - Trend Analysis
  - Error Handling
- WebSocket Communication (81%)
  - Connection Management
  - Message Broadcasting
  - Error Handling
  - Data Validation

### Medium Coverage Areas (70-90%)
- Audio Detection
- WebSocket Communication
- Station Management

#### Areas Needing Improvement (<70%)
- External Service Integration
- Error Recovery Scenarios
- Performance Testing

### Recent Improvements
1. **Redis Configuration Tests**
   - Added comprehensive connection testing
   - Improved error handling coverage
   - Added password authentication tests
   - Implemented cleanup utilities

2. **Test Organization**
   - Consolidated API tests
   - Improved test isolation
   - Enhanced mock implementations
   - Better error simulation

3. **Documentation**
   - Updated test coverage metrics
   - Added new test categories
   - Improved setup instructions
   - Enhanced troubleshooting guide 

### Recent Test Improvements
1. **Analytics Testing**
   - Added comprehensive stats update tests
   - Implemented report generation validation
   - Enhanced trend analysis coverage
   - Added error handling scenarios
   - Improved data validation
2. **WebSocket Testing**
   - Added reconnection scenario tests
   - Implemented failed connection handling
   - Enhanced message validation
   - Added maximum connection limit tests
   - Improved error handling coverage
   - Added data validation for track detection
   - Implemented connection cleanup
   - Added comprehensive error scenarios 

## Modules de Test

### 1. WebSocket (`test_websocket.py`)
Tests pour la gestion des connexions WebSocket en temps réel.

#### Tests de Connexion
- `test_connection_manager_connect`: Établissement de connexion
- `test_connection_manager_disconnect`: Déconnexion
- `test_connection_manager_max_connections`: Limite de connexions

#### Tests de Diffusion
- `test_connection_manager_broadcast`: Diffusion de messages
- `test_connection_manager_broadcast_with_failed_connection`: Gestion des échecs
- `test_send_heartbeat`: Envoi de heartbeats

#### Tests de Messages
- `test_process_websocket_message_heartbeat`: Traitement des heartbeats
- `test_process_websocket_message_invalid_json`: Messages JSON invalides
- `test_process_websocket_message_unknown_type`: Types de messages inconnus
- `test_process_websocket_message_validation`: Validation des messages

#### Tests d'Intégration Redis
- `test_redis_integration`: Intégration avec Redis pour la diffusion

### 2. Redis Configuration (`test_redis_config.py`)
Tests pour la configuration et la gestion de Redis.

#### Tests de Configuration
- `test_get_redis_success`: Création réussie du client
- `test_get_redis_with_password`: Authentification avec mot de passe
- `test_get_redis_connection_error`: Gestion des erreurs de connexion
- `test_get_redis_invalid_settings`: Paramètres invalides
- `test_get_redis_timeout`: Timeouts de connexion

#### Tests de Connexion
- `test_check_redis_connection_success`: Vérification de connexion réussie
- `test_check_redis_connection_failure`: Échec de connexion
- `test_check_redis_connection_no_client`: Absence de client

#### Tests Pub/Sub
- `test_redis_pubsub`: Fonctionnalité pub/sub
- `test_redis_connection_pool`: Configuration du pool de connexions
- `test_redis_ssl_config`: Configuration SSL
- `test_redis_max_connections`: Limite de connexions

### 3. Stream Checker (`test_stream_checker.py`)
Tests pour la vérification des flux radio.

#### Tests de Disponibilité
- `test_check_stream_availability_success`: Vérification réussie
- `test_check_stream_availability_not_audio`: Contenu non-audio
- `test_check_stream_availability_timeout`: Timeouts
- `test_check_stream_availability_error`: Erreurs client

#### Tests de Métadonnées
- `test_get_stream_metadata_success`: Récupération réussie
- `test_get_stream_metadata_no_metadata`: Absence de métadonnées
- `test_get_stream_metadata_timeout`: Timeouts
- `test_get_stream_metadata_error`: Erreurs client

### 4. Track Detection (`test_track_detection.py`)
Tests pour la détection des morceaux.

#### Tests de Détection
- `test_detect_music_vs_speech`: Différenciation musique/parole
- `test_local_detection_success`: Détection locale
- `test_musicbrainz_fallback`: Fallback MusicBrainz
- `test_audd_fallback`: Fallback Audd
- `test_all_detection_methods_fail`: Échec de toutes les méthodes

#### Tests de Confiance
- `test_low_confidence_results`: Résultats peu fiables
- `test_feature_extraction`: Extraction de caractéristiques

#### Tests d'Erreur
- `test_error_handling`: Gestion des erreurs
- `test_detection_with_missing_api_keys`: Clés API manquantes

### Mocking HTTP avec aioresponses
```python
@pytest.mark.asyncio
async def test_check_stream_availability(mock_aioresponse):
    """Test stream availability check with mocked HTTP responses."""
    url = "http://test.stream"
    mock_aioresponse.head(url, status=200, headers={'content-type': 'audio/mpeg'})
    
    result = await check_stream_availability(url)
    assert result['is_available'] is True
    assert result['is_audio_stream'] is True
```

### Tests de Métadonnées de Flux
```python
@pytest.mark.asyncio
async def test_get_stream_metadata(mock_aioresponse):
    """Test stream metadata retrieval with mocked response."""
    url = "http://test.stream"
    mock_aioresponse.get(url, status=200, headers={
        'icy-name': 'Test Radio',
        'icy-genre': 'Test Genre',
        'icy-br': '128'
    })
    
    result = await get_stream_metadata(url)
    assert result == {
        'name': 'Test Radio',
        'genre': 'Test Genre',
        'bitrate': '128'
    }
```

### Tests d'Authentification avec Datetime Mock
```python
@patch('backend.utils.auth.datetime')
def test_create_access_token(mock_datetime):
    """Test token creation with mocked datetime."""
    fixed_time = datetime(2025, 1, 1, 12, 0)
    mock_datetime.now.return_value = fixed_time
    
    data = {"sub": "test@example.com"}
    token = create_access_token(data)
    
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    expected_exp = int(fixed_time.timestamp()) + 15 * 60
    assert payload["exp"] == expected_exp
``` 