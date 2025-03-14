# Exécution des Tests Unitaires

Ce document explique comment exécuter les tests unitaires du projet SODAV Monitor.

## Prérequis

Avant d'exécuter les tests, assurez-vous que :

1. L'environnement virtuel Python est activé
2. Toutes les dépendances sont installées : `pip install -r requirements.txt`
3. Les variables d'environnement sont correctement configurées (fichier `.env.development` ou `.env.test`)

## Structure des Tests

Les tests sont organisés selon la structure du projet :

```
backend/tests/
├── api/                  # Tests des API
├── detection/            # Tests des modules de détection
│   ├── audio_processor/  # Tests du processeur audio
│   │   ├── track_manager/# Tests du gestionnaire de pistes
│   │   │   ├── test_track_creator.py
│   │   │   ├── test_track_finder.py
│   │   │   ├── test_external_detection.py
│   │   │   ├── test_fingerprint_handler.py
│   │   │   └── test_stats_recorder.py
│   │   └── ...
│   └── ...
├── models/               # Tests des modèles de données
├── utils/                # Tests des utilitaires
└── ...
```

## Commandes d'Exécution des Tests

### Exécuter tous les tests

```bash
cd backend
python -m pytest
```

### Exécuter les tests d'un module spécifique

```bash
cd backend
python -m pytest tests/detection/audio_processor/track_manager/
```

### Exécuter un fichier de test spécifique

```bash
cd backend
python -m pytest tests/detection/audio_processor/track_manager/test_track_creator.py
```

### Exécuter un test spécifique

```bash
cd backend
python -m pytest tests/detection/audio_processor/track_manager/test_track_creator.py::test_get_or_create_artist_new
```

## Tests du Module TrackManager

Le module TrackManager a été refactorisé en plusieurs classes spécialisées, chacune avec ses propres tests unitaires. Voici comment exécuter ces tests :

### Exécuter tous les tests du module TrackManager

```bash
cd backend
python -m pytest tests/detection/audio_processor/track_manager/ -v
```

### Exécuter les tests d'une classe spécifique

```bash
# Tests de TrackCreator
python -m pytest tests/detection/audio_processor/track_manager/test_track_creator.py -v

# Tests de TrackFinder
python -m pytest tests/detection/audio_processor/track_manager/test_track_finder.py -v

# Tests de ExternalDetectionService
python -m pytest tests/detection/audio_processor/track_manager/test_external_detection.py -v

# Tests de FingerprintHandler
python -m pytest tests/detection/audio_processor/track_manager/test_fingerprint_handler.py -v

# Tests de StatsRecorder
python -m pytest tests/detection/audio_processor/track_manager/test_stats_recorder.py -v
```

### Exécuter un test spécifique

```bash
# Exemple : test de la méthode get_or_create_track_new
python -m pytest tests/detection/audio_processor/track_manager/test_track_creator.py::test_get_or_create_track_new -v
```

### Notes sur les Tests du Module TrackManager

1. **Dépendances Externes** : Certains tests du module FingerprintHandler nécessitent des bibliothèques externes comme `librosa` et `acoustid.chromaprint`. Si ces bibliothèques ne sont pas disponibles, les tests utiliseront des implémentations de secours.

2. **Tests Asynchrones** : De nombreux tests du module TrackManager sont asynchrones et utilisent le décorateur `@pytest.mark.asyncio`. Assurez-vous que le plugin `pytest-asyncio` est installé.

3. **Mocks** : Les tests utilisent intensivement des mocks pour simuler les dépendances externes comme les sessions de base de données et les appels HTTP. Assurez-vous que le plugin `pytest-mock` est installé.

4. **Environnement de Test** : Certains tests nécessitent des variables d'environnement spécifiques. Consultez le fichier `.env.test` pour plus d'informations.

## Options Utiles

### Mode Verbeux

Pour afficher plus de détails sur les tests exécutés :

```bash
python -m pytest -v
```

### Afficher les Logs

Pour afficher les logs pendant l'exécution des tests :

```bash
python -m pytest --log-cli-level=INFO
```

### Mesurer la Couverture de Code

Pour mesurer la couverture de code des tests :

```bash
python -m pytest --cov=backend
```

Pour générer un rapport HTML de couverture :

```bash
python -m pytest --cov=backend --cov-report=html
```

Le rapport sera généré dans le dossier `htmlcov/`.

## Résolution des Problèmes Courants

### Erreur d'Importation

Si vous rencontrez des erreurs d'importation, vérifiez que :

1. Vous exécutez les tests depuis le répertoire `backend`
2. Le module `backend` est dans le PYTHONPATH
3. Les dépendances sont correctement installées

### Erreurs de Base de Données

Si vous rencontrez des erreurs liées à la base de données :

1. Vérifiez que la variable d'environnement `DATABASE_URL` est correctement configurée
2. Assurez-vous que la base de données de test existe et est accessible
3. Vérifiez que les migrations sont à jour

### Tests Asynchrones

Pour les tests asynchrones, assurez-vous d'utiliser le décorateur `@pytest.mark.asyncio` et d'installer le plugin `pytest-asyncio`.

## Bonnes Pratiques

1. **Exécutez les tests régulièrement** pendant le développement
2. **Écrivez des tests pour chaque nouvelle fonctionnalité** avant de l'implémenter (TDD)
3. **Maintenez une couverture de code élevée** (minimum 90%)
4. **Utilisez des mocks** pour isoler les composants et simuler les dépendances externes
5. **Documentez les scénarios de test** pour faciliter la compréhension

## Ressources Supplémentaires

- [Documentation officielle de pytest](https://docs.pytest.org/)
- [Guide de pytest-asyncio](https://pytest-asyncio.readthedocs.io/en/latest/)
- [Guide de pytest-cov](https://pytest-cov.readthedocs.io/en/latest/)
