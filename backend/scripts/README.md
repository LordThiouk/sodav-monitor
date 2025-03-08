# Scripts du Backend

Ce dossier contient divers scripts utilitaires pour le backend du projet SODAV Monitor.

## Organisation des scripts

Les scripts sont organisés dans les sous-dossiers suivants :

- `admin/` - Scripts pour les tâches administratives
- `database/` - Scripts pour la gestion de la base de données
- `detection/` - Scripts pour la détection musicale
- `maintenance/` - Scripts pour la maintenance du système
- `migrations/` - Scripts pour les migrations de la base de données
- `performance/` - Scripts pour les tests de performance
- `startup/` - Scripts pour le démarrage du système
- `tests/` - Scripts pour les tests unitaires et d'intégration

## Scripts de test des services externes

Les scripts suivants sont utilisés pour tester les services externes de détection musicale :

### Tests MusicBrainz

- `test_musicbrainz_simple.py` - Test simple de l'API MusicBrainz
- `test_musicbrainz_metadata.py` - Test de la recherche par métadonnées avec MusicBrainz

### Tests AcoustID

- `test_acoustid_simple.py` - Test simple de l'API AcoustID
- `test_acoustid_format.py` - Test des formats audio avec AcoustID
- `test_acoustid_fpcalc.py` - Test de l'outil fpcalc pour AcoustID

### Tests AudD

- `test_audd_simple.py` - Test simple de l'API AudD
- `test_audd_url.py` - Test de l'API AudD avec des URLs
- `test_audd_url_simple.py` - Test simple de l'API AudD avec des URLs

### Tests combinés

- `test_api_keys.py` - Test des clés API pour tous les services externes
- `test_external_services.py` - Test de tous les services externes
- `test_detection_hierarchy.py` - Test du processus de détection hiérarchique complet

## Comment exécuter les scripts

Pour exécuter un script, utilisez la commande suivante depuis la racine du projet :

```bash
python backend/scripts/nom_du_script.py
```

Par exemple, pour tester le processus de détection hiérarchique :

```bash
python backend/scripts/test_detection_hierarchy.py
```

## Organisation recommandée des scripts

Pour une meilleure organisation, nous recommandons de déplacer les scripts de test des services externes dans le sous-dossier `detection/` :

```bash
mkdir -p backend/scripts/detection/external_services
mv backend/scripts/test_*_simple.py backend/scripts/detection/external_services/
mv backend/scripts/test_*_url*.py backend/scripts/detection/external_services/
mv backend/scripts/test_*_format.py backend/scripts/detection/external_services/
mv backend/scripts/test_*_fpcalc.py backend/scripts/detection/external_services/
mv backend/scripts/test_api_keys.py backend/scripts/detection/external_services/
mv backend/scripts/test_external_services.py backend/scripts/detection/external_services/
mv backend/scripts/test_detection_hierarchy.py backend/scripts/detection/
```

Après cette réorganisation, les scripts peuvent être exécutés comme suit :

```bash
python backend/scripts/detection/external_services/test_musicbrainz_simple.py
python backend/scripts/detection/test_detection_hierarchy.py
```

## Structure des Dossiers

```
backend/scripts/
├── startup/                # Scripts de démarrage de l'application
│   ├── start_env.ps1       # Script PowerShell pour démarrer l'application
│   └── start_env.sh        # Script Bash pour démarrer l'application
│
├── database/               # Scripts liés à la base de données
│   ├── fix_db_schema.py    # Correction du schéma de la base de données
│   └── update_db_schema.py # Mise à jour du schéma de la base de données
│
├── migrations/             # Scripts liés aux migrations de la base de données
│   ├── run_migration.py    # Exécution des migrations
│   ├── check_migration.py  # Vérification des migrations
│   ├── check_alembic_version.py # Vérification de la version d'Alembic
│   ├── update_alembic_revision.py # Mise à jour de la révision Alembic
│   └── run_updated_at_tests.py # Tests sur les champs updated_at
│
├── tests/                  # Scripts liés aux tests
│   ├── run_all_tests.sh    # Exécution de tous les tests
│   ├── run_tests.py        # Utilitaire Python pour exécuter les tests
│   ├── run_integration_tests.sh # Exécution des tests d'intégration
│   └── fix_integration_tests.sh # Correction des tests d'intégration
│
├── performance/            # Scripts liés aux tests de performance
│   ├── generate_report.py  # Génération de rapports de performance
│   └── run_station_monitoring_tests.py # Tests de performance du monitoring des stations
│
├── maintenance/            # Scripts de maintenance du code
│   ├── reorganize.py       # Réorganisation des fichiers
│   ├── reorganize_backend.py # Réorganisation spécifique au backend
│   ├── update_imports.py   # Mise à jour des imports
│   └── update_fastapi_lifespan.py # Mise à jour du cycle de vie FastAPI
│
├── detection/              # Scripts liés à la détection musicale
│   ├── detect_music_all_stations.py # Détection sur toutes les stations
│   ├── test_music_detection.py      # Test de la détection musicale
│   └── check_detection_results.py   # Vérification des résultats de détection
│
├── data/                   # Scripts liés aux données
│   ├── seed_test_data.py          # Génération de données de test
│   ├── create_test_audio.py       # Création d'audio de test
│   ├── fetch_senegal_stations.py  # Récupération des stations sénégalaises
│   └── clean_db.py                # Nettoyage de la base de données
│
└── admin/                  # Scripts d'administration
    └── create_admin_user.py       # Création d'utilisateurs administrateurs
```

## Utilisation

### Scripts de Démarrage

Pour démarrer l'application dans différents environnements :

```bash
# Windows (PowerShell)
.\backend\scripts\startup\start_env.ps1 development
.\backend\scripts\startup\start_env.ps1 production

# Linux/Mac (Bash)
./backend/scripts/startup/start_env.sh development
./backend/scripts/startup/start_env.sh production
```

### Scripts de Test

Pour exécuter les tests :

```bash
# Tous les tests
python -m backend.scripts.tests.run_tests

# Tests d'intégration
./backend/scripts/tests/run_integration_tests.sh
```

### Scripts de Base de Données

Pour gérer la base de données :

```bash
# Mise à jour du schéma
python -m backend.scripts.database.update_db_schema

# Correction du schéma
python -m backend.scripts.database.fix_db_schema

# Exécution des migrations
python -m backend.scripts.migrations.run_migration
```

### Scripts de Performance

Pour exécuter les tests de performance :

```bash
# Tests de performance du monitoring des stations
python -m backend.scripts.performance.run_station_monitoring_tests

# Génération de rapports de performance
python -m backend.scripts.performance.generate_report
```

### Scripts d'Administration

Pour créer un utilisateur administrateur :

```bash
python -m backend.scripts.admin.create_admin_user --username admin --email admin@sodav.sn --password secure_password
```

## Remarques

- Tous les scripts sont conçus pour être exécutés depuis la racine du projet.
- Les scripts de démarrage créent automatiquement les répertoires nécessaires s'ils n'existent pas.
- Pour plus d'informations sur chaque script, consultez la documentation en haut de chaque fichier. 