# Scripts Utilitaires pour SODAV Monitor

Ce répertoire contient tous les scripts utilitaires pour le projet SODAV Monitor, organisés par catégorie.

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