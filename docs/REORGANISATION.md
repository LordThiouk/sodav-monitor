# Réorganisation du Backend SODAV Monitor

## Vue d'ensemble
Ce document suit les changements majeurs effectués lors de la réorganisation du backend du projet SODAV Monitor.

## Journal des modifications

### 2024-03-21
- Correction des erreurs de linter dans `routers/reports.py`:
  - Réorganisation des arguments dans `generate_daily_report` et `generate_monthly_report`
  - Respect de la convention Python pour l'ordre des arguments (arguments positionnels avant les arguments par défaut)

### 2024-03-22
- Réorganisation des routeurs FastAPI :
  - `analytics.py` : Statistiques et analyses des détections
  - `channels.py` : Gestion des stations radio (CRUD, statut, monitoring)
  - `detections.py` : Gestion des détections musicales en temps réel
  - `reports.py` : Génération et gestion des rapports
  - `auth.py` : Authentification et gestion des utilisateurs
  - `websocket.py` : Communication en temps réel

### 2024-03-23
- Amélioration du routeur des rapports (`reports.py`) :
  - Ajout de la gestion des abonnements aux rapports (création, liste, suppression)
  - Implémentation de l'envoi de rapports par email
  - Amélioration de la gestion des erreurs et du logging
  - Ajout de la pagination pour les listes de rapports et d'abonnements

### 2024-03-24
- Réorganisation du module de détection audio :
  - Création du package `detection/audio_processor/` avec sous-modules spécialisés :
    - `core.py` : Processeur audio principal
    - `stream_handler.py` : Gestion des flux audio
    - `feature_extractor.py` : Extraction des caractéristiques audio
    - `track_manager.py` : Gestion des pistes détectées
    - `station_monitor.py` : Monitoring des stations radio
  - Améliorations de performance :
    - Optimisation de l'utilisation de la mémoire
    - Traitement parallèle des flux audio
    - Mise en cache des empreintes digitales fréquentes
  - Gestion avancée des ressources :
    - Limitation du nombre de stations traitées simultanément
    - Contrôle de l'utilisation de la mémoire
    - Timeouts pour les opérations longues

### 2024-03-25
- Nettoyage et consolidation des tests backend :
  - Fusion des tests API redondants en un seul fichier `test_api.py`
  - Suppression des fichiers redondants :
    - `test_api_dir.py`
    - `test_api_direct.py`
    - `test_websocket.py`
  - Amélioration des tests API :
    - Ajout de tests paramétrés pour les endpoints
    - Meilleure gestion des erreurs
    - Tests de workflow complets pour les stations et détections
    - Tests WebSocket intégrés
    - Utilisation de la configuration depuis `core.config`

## Objectifs de la réorganisation
- Améliorer la maintenabilité du code
- Réduire la taille des fichiers
- Séparer les responsabilités
- Faciliter les tests unitaires
- Améliorer la gestion des erreurs
- Optimiser les performances

## Changements majeurs

### 1. Structure des dossiers
- Réorganisation en modules fonctionnels :
  ```
  backend/
  ├── analytics/        # Analyses et statistiques
  ├── detection/        # Détection musicale
  │   └── audio_processor/
  │       ├── core.py
  │       ├── stream_handler.py
  │       ├── feature_extractor.py
  │       ├── track_manager.py
  │       └── station_monitor.py
  ├── logs/            # Gestion des logs
  ├── models/          # Modèles de données
  ├── processing/      # Traitement des données
  ├── reports/         # Génération de rapports
  ├── routers/         # Routes FastAPI
  ├── tests/          # Tests unitaires
  └── utils/          # Utilitaires
  ```

### 2. Routeurs FastAPI
Séparation des routes en modules distincts avec responsabilités spécifiques :

#### Analytics (`analytics.py`)
- Vue d'ensemble du tableau de bord
- Statistiques par station et artiste
- Analyse des tendances
- Métriques de performance

#### Channels (`channels.py`)
- CRUD des stations radio
- Monitoring des flux
- Gestion des statuts
- Statistiques par station

#### Detections (`detections.py`)
- Gestion des détections en temps réel
- Traitement audio
- Historique des détections
- Filtrage et recherche

#### Reports (`reports.py`)
- Génération de rapports (PDF, Excel, CSV)
- Planification des rapports
- Gestion des abonnements
  - Création d'abonnements personnalisés
  - Liste des abonnements actifs
  - Suppression d'abonnements
- Distribution des rapports
  - Envoi par email
  - Téléchargement direct
  - Formats multiples (PDF, Excel, CSV)
- Rapports périodiques
  - Rapports quotidiens
  - Rapports mensuels
  - Rapports personnalisés

#### Auth (`auth.py`)
- Authentification des utilisateurs
- Gestion des sessions
- Réinitialisation des mots de passe
- Gestion des rôles

#### WebSocket (`websocket.py`)
- Communication en temps réel
- Diffusion des détections
- Gestion des connexions
- Heartbeat et monitoring

### 3. Améliorations techniques

#### Gestion des erreurs
- Logging structuré avec niveaux de gravité
- Traçabilité des erreurs
- Notifications en temps réel
- Métriques de monitoring

#### Performance
- Optimisation des requêtes SQL
- Mise en cache Redis
- Traitement asynchrone
- Pagination des résultats

#### Monitoring
- Métriques système en temps réel
- Alertes automatiques
- Tableaux de bord de performance
- Journalisation des événements

## Prochaines étapes
1. Implémentation de tests de charge
2. Documentation API avec Swagger
3. Optimisation des requêtes SQL
4. Mise en place de l'intégration continue
5. Configuration du déploiement automatique 