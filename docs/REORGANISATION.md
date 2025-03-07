# Réorganisation du Projet SODAV Monitor

Ce document retrace les principales modifications apportées à la structure du projet SODAV Monitor pour améliorer son organisation et sa maintenabilité.

## Dernières Modifications

### 07/03/2025 - Élimination des Redondances et Réorganisation des Scripts

#### 1. Élimination de la Redondance `backend/backend`

- **Problème identifié** : Une structure redondante `backend/backend` existait, créant une confusion dans l'organisation des fichiers.
- **Solution** : 
  - Modification de `config.py` pour utiliser `os.path.dirname(os.path.abspath(__file__))` comme valeur pour `BACKEND_DIR`
  - Déplacement du contenu des dossiers `backend/backend/data`, `backend/backend/logs`, `backend/backend/models` et `backend/backend/reports` vers leurs équivalents dans le dossier `backend` principal
  - Suppression du dossier redondant `backend/backend`

#### 2. Réorganisation des Scripts

- **Problème identifié** : Deux dossiers de scripts existaient (`/scripts` à la racine et `backend/scripts`), créant une confusion sur l'emplacement des scripts utilitaires.
- **Solution** : 
  - Centralisation de tous les scripts dans `backend/scripts/`
  - Organisation des scripts par catégorie dans des sous-dossiers :
    - `startup/` : Scripts de démarrage de l'application
    - `admin/` : Scripts d'administration
    - `data/` : Scripts de gestion des données
    - `detection/` : Scripts de détection musicale
    - `tests/` : Scripts de tests
    - `database/` : Scripts de base de données
    - `migrations/` : Scripts de migrations de la base de données
    - `performance/` : Scripts de tests de performance
    - `maintenance/` : Scripts de maintenance
  - Mise à jour de la documentation pour refléter la nouvelle organisation

#### 3. Mise à jour des Chemins dans les Fichiers de Configuration

- **Modification** : Mise à jour des chemins dans `.env.example`, `.env.development` et `.env.production` pour utiliser des chemins relatifs simples
- **Avantage** : Élimination des chemins redondants et simplification de la configuration

#### 4. Mise à jour des Scripts de Démarrage

- **Modification** : Mise à jour de `start_env.ps1` et `start_env.sh` pour créer automatiquement les répertoires nécessaires
- **Avantage** : Simplification du processus de démarrage et garantie que tous les dossiers requis existent

## Avantages de la Nouvelle Organisation

1. **Structure plus claire** : Élimination des redondances et organisation logique des fichiers
2. **Maintenance simplifiée** : Regroupement des scripts par fonctionnalité pour une meilleure maintenabilité
3. **Documentation améliorée** : Mise à jour de la documentation pour refléter la nouvelle organisation
4. **Démarrage simplifié** : Création automatique des dossiers nécessaires au démarrage de l'application
5. **Cohérence** : Utilisation de chemins relatifs cohérents dans tous les fichiers de configuration

## Prochaines Étapes

- Mettre à jour les imports dans les scripts pour refléter la nouvelle structure
- Vérifier que tous les scripts fonctionnent correctement avec la nouvelle organisation
- Mettre à jour la documentation supplémentaire si nécessaire
