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

### 3. Tests End-to-End (E2E)

Les tests end-to-end vérifient le fonctionnement complet du système dans des conditions réelles :

- **integration/** : Tests d'intégration et end-to-end
  - `test_end_to_end.py` : Tests end-to-end complets du système
  - **detection/** : Tests d'intégration de détection
    - `test_play_duration_real_data.py` : Tests de durée de lecture avec des données réelles
    - `test_continuous_play_duration.py` : Tests de durée de lecture continue
    - `test_real_data_detection.py` : Tests de détection avec des données réelles
  - **api/** : Tests d'intégration API
  - **analytics/** : Tests d'intégration des analyses

Pour plus d'informations sur les tests end-to-end, consultez [README_E2E_TESTS.md](integration/README_E2E_TESTS.md).

## Exécution des Tests

### Tests Unitaires

```bash
# Exécuter tous les tests unitaires
python -m pytest backend/tests/ -v

# Exécuter un test spécifique
python -m pytest backend/tests/detection/test_track_manager.py -v
```

### Tests d'Intégration

```bash
# Exécuter tous les tests d'intégration
python -m pytest backend/tests/integration/ -v

# Exécuter un test d'intégration spécifique
python -m pytest backend/tests/integration/detection/test_detection_integration.py -v
```

### Tests End-to-End

```bash
# Exécuter tous les tests end-to-end
python -m pytest backend/tests/integration/test_end_to_end.py -v

# Exécuter un test end-to-end spécifique
python -m pytest backend/tests/integration/test_end_to_end.py::TestEndToEnd::test_detection_workflow -v

# Exécuter avec sortie de logs
python -m pytest backend/tests/integration/test_end_to_end.py -v --log-cli-level=INFO
```

## Couverture des Tests

Pour générer un rapport de couverture des tests :

```bash
# Générer un rapport de couverture
python -m pytest --cov=backend backend/tests/

# Générer un rapport HTML détaillé
python -m pytest --cov=backend --cov-report=html backend/tests/
```

Le rapport HTML sera disponible dans le répertoire `htmlcov/`.

## Bonnes Pratiques

1. **Isolation** : Chaque test doit être indépendant des autres
2. **Mocks** : Utiliser des mocks pour les dépendances externes
3. **Fixtures** : Utiliser des fixtures pour partager la configuration
4. **Nommage** : Suivre la convention de nommage `test_<fonction_testée>.py`
5. **Documentation** : Documenter les tests complexes
6. **Couverture** : Viser une couverture de code d'au moins 90%
7. **Données de Test** : Utiliser des données de test réalistes
8. **Performance** : Optimiser les tests pour qu'ils s'exécutent rapidement

## Tests avec Données Réelles

Pour les tests nécessitant des données réelles (comme les tests de détection musicale), nous utilisons :

1. **Fichiers Audio de Test** : Stockés dans `backend/tests/data/audio/`
2. **Flux Radio Réels** : Stations de radio sénégalaises accessibles via Internet
3. **Empreintes Digitales** : Empreintes digitales pré-calculées pour les tests

Pour les tests end-to-end, nous utilisons des stations de radio sénégalaises réelles pour garantir des conditions de test authentiques.
