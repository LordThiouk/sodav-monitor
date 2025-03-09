# Tests pour SODAV Monitor

Ce répertoire contient tous les tests pour le backend du projet SODAV Monitor.

## Structure des Tests

Les tests sont organisés selon les principes suivants :

### 1. Tests Unitaires

Les tests unitaires vérifient le fonctionnement isolé de composants spécifiques :

- **analytics/** : Tests des fonctionnalités d'analyse
  - `test_analytics.py` : Tests de base des fonctionnalités d'analyse
  - `test_analytics_manager.py` : Tests du gestionnaire d'analyses
  - `test_generate_detections.py` : Tests de génération de données de détection
  - `test_generate_test_report.py` : Tests de génération de rapports

- **api/** : Tests des endpoints API
  - `test_detections_api.py` : Tests des endpoints de détection
  - `test_music_detection_api.py` : Tests des endpoints de détection musicale
  - `test_analytics_api.py` : Tests des endpoints d'analyse
  - `test_reports_api.py` : Tests des endpoints de rapports
  - `test_reports_router.py` : Tests du routeur de rapports réorganisé
  - `test_websocket.py` : Tests de communication WebSocket
  - `test_api_performance.py` : Tests de performance des endpoints API

- **auth/** : Tests d'authentification
  - `test_auth.py` : Tests des fonctionnalités d'authentification

- **detection/** : Tests de détection musicale
  - `test_detection.py` : Tests de la fonctionnalité principale de détection
  - `test_track_manager.py` : Tests de gestion des pistes
  - `test_station_monitor.py` : Tests de surveillance des stations
  - `test_stream_handler.py` : Tests de gestion des flux
  - `test_feature_extractor.py` : Tests d'extraction de caractéristiques
  - `test_fingerprint.py` : Tests d'empreintes digitales audio
  - **audio_processor/** : Tests du processeur audio
    - `test_core.py` : Tests de la fonctionnalité de base du processeur audio
    - `test_stream_handler.py` : Tests de gestion des flux
    - `test_feature_extractor.py` : Tests d'extraction de caractéristiques
    - `test_audio_analysis.py` : Tests des algorithmes d'analyse audio
    - `test_local_detection.py` : Tests de détection locale d'empreintes
    - `test_external_services.py` : Tests des services de reconnaissance musicale externes
    - `test_hierarchical_detection.py` : Tests du pipeline de détection hiérarchique
    - `test_external_integration.py` : Tests d'intégration avec des services externes
    - `test_performance.py` : Tests de performance pour le traitement audio
  - **external/** : Tests des services externes
    - `test_external_services.py` : Tests des fonctionnalités générales des services externes
    - `test_musicbrainz_recognizer.py` : Tests d'intégration MusicBrainz/AcoustID

- **reports/** : Tests de génération de rapports
  - `test_reports.py` : Tests de la fonctionnalité de base des rapports
  - `test_generator.py` : Tests du générateur de rapports
  - `test_report_generator.py` : Tests de génération de rapports
  - `test_subscription_handler.py` : Tests de gestion des abonnements aux rapports

- **utils/** : Tests des utilitaires
  - `test_auth.py` : Tests des utilitaires d'authentification
  - `test_redis_config.py` : Tests de configuration Redis
  - `test_validators.py` : Tests des validateurs de données
  - `test_file_manager.py` : Tests des utilitaires de gestion de fichiers
  - `test_logging_config.py` : Tests de configuration de journalisation

### 2. Tests d'Intégration

Les tests d'intégration vérifient l'interaction entre différents composants du système :

- **integration/** : Tests d'intégration
  - **api/** : Tests d'intégration des endpoints API
    - `test_api_endpoints.py` : Tests de tous les endpoints API
    - `test_api_integration.py` : Tests d'intégration de l'API avec d'autres composants
  - **detection/** : Tests d'intégration du système de détection
    - `test_detection_integration.py` : Tests d'intégration de base pour la détection
    - `test_detection_pipeline.py` : Tests du pipeline complet de détection
  - **analytics/** : Tests d'intégration du système d'analyse
    - `test_analytics_integration.py` : Tests d'intégration de base pour l'analyse
    - `test_analytics_pipeline.py` : Tests du pipeline complet d'analyse

### 3. Tests de Performance

- **performance/** : Tests de performance
  - Tests de charge et de stress pour les composants critiques
  - Benchmarks pour les opérations intensives

## Exécution des Tests

### Exécuter tous les tests

```bash
python -m pytest
```

### Exécuter des tests spécifiques

```bash
# Tests unitaires
python -m pytest backend/tests/api/
python -m pytest backend/tests/detection/

# Tests d'intégration
python -m pytest backend/tests/integration/

# Tests de performance
python -m pytest backend/tests/performance/
```

### Exécuter un test spécifique

```bash
python -m pytest backend/tests/api/test_detections_api.py::TestDetectionsAPI::test_get_detections
```

## Fixtures

Les fixtures partagées sont définies dans les fichiers `conftest.py` à différents niveaux :

- `backend/tests/conftest.py` : Fixtures globales pour tous les tests
- `backend/tests/integration/conftest.py` : Fixtures spécifiques aux tests d'intégration
- `backend/tests/detection/conftest.py` : Fixtures spécifiques aux tests de détection
- etc.

## Bonnes Pratiques

1. **Isolation** : Chaque test doit être indépendant des autres
2. **Mocking** : Utiliser des mocks pour les services externes
3. **Nommage** : Suivre la convention `test_<fonctionnalité>.py`
4. **Documentation** : Documenter clairement l'objectif de chaque test
5. **Couverture** : Viser une couverture de code d'au moins 90% 