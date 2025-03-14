# Exécution des Tests End-to-End avec GitHub Actions

Ce document explique comment utiliser GitHub Actions pour exécuter les tests end-to-end du système SODAV Monitor sans avoir besoin d'installer Docker localement.

## Avantages de l'utilisation de GitHub Actions

- Aucune installation locale requise
- Exécution dans un environnement isolé et propre
- Ressources de calcul fournies par GitHub
- Résultats des tests facilement accessibles
- Intégration avec le système de CI/CD

## Workflows Disponibles

Le système SODAV Monitor propose plusieurs workflows GitHub Actions pour les tests end-to-end :

### 1. E2E Tests with Docker (`.github/workflows/e2e_tests_docker.yml`)

Ce workflow utilise Docker pour créer un environnement complet avec tous les services nécessaires (PostgreSQL, Redis, etc.) et exécute les tests end-to-end dans cet environnement.

### 2. E2E Tests Local (`.github/workflows/e2e_tests_local.yml`)

Ce workflow exécute les tests end-to-end sans Docker, en utilisant directement les services PostgreSQL et Redis fournis par GitHub Actions.

### 3. E2E Tests with Pydantic Compatibility (`.github/workflows/e2e_tests_pydantic_compat.yml`)

Ce workflow est spécialement conçu pour gérer les problèmes de compatibilité avec Pydantic v1 et v2. Il crée automatiquement une couche de compatibilité pour permettre l'utilisation des fonctionnalités de Pydantic v2 avec Pydantic v1.

### 4. Run E2E Tests on Push (`.github/workflows/run_on_push.yml`)

Ce workflow est exécuté automatiquement à chaque push sur n'importe quelle branche. Il:
- Configure un environnement avec PostgreSQL et Redis
- Installe les dépendances nécessaires
- Crée la couche de compatibilité Pydantic
- Démarre le serveur backend
- Exécute les tests end-to-end
- Télécharge les résultats des tests comme artefacts

Ce workflow est idéal pour la validation continue du code, car il s'exécute à chaque modification.

## Configuration

Les workflows GitHub Actions pour les tests end-to-end sont définis dans les fichiers `.github/workflows/`. Ces workflows :

1. Configurent l'environnement nécessaire (avec ou sans Docker)
2. Installent les dépendances requises
3. Exécutent les tests end-to-end
4. Génèrent des rapports HTML
5. Téléchargent les rapports comme artefacts

## Prérequis

Avant de pouvoir exécuter les tests, vous devez configurer les secrets GitHub suivants :

1. `ACOUSTID_API_KEY` : Votre clé API pour le service AcoustID
2. `AUDD_API_KEY` : Votre clé API pour le service AudD

### Configuration des secrets GitHub

1. Accédez aux paramètres de votre dépôt GitHub
2. Cliquez sur "Secrets and variables" puis "Actions"
3. Cliquez sur "New repository secret"
4. Ajoutez les secrets `ACOUSTID_API_KEY` et `AUDD_API_KEY` avec vos clés API

## Exécution des Tests

### Exécution Manuelle

1. Accédez à l'onglet "Actions" de votre dépôt GitHub
2. Sélectionnez le workflow que vous souhaitez exécuter dans la barre latérale
3. Cliquez sur le bouton "Run workflow"
4. Sélectionnez la branche sur laquelle exécuter les tests
5. Cliquez sur "Run workflow"

### Exécution Automatique

Les workflows sont également configurés pour s'exécuter automatiquement :
- Chaque lundi à minuit (UTC) pour les workflows programmés
- À chaque push sur les branches `main` et `develop` pour certains workflows
- À chaque push sur n'importe quelle branche pour le workflow `run_on_push.yml`

### Exécution Locale avec Act

Vous pouvez également exécuter les workflows GitHub Actions localement à l'aide de l'outil [act](https://github.com/nektos/act) :

1. Installez act :
   ```bash
   # macOS
   brew install act

   # Linux
   curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
   ```

2. Exécutez le workflow :
   ```bash
   # Exécuter le workflow E2E avec Pydantic compatibility
   ./run_github_actions_locally.sh

   # Ou directement avec act
   act -j e2e-tests -W .github/workflows/e2e_tests_pydantic_compat.yml --bind

   # Exécuter le workflow qui s'exécute à chaque push
   act -j e2e-tests -W .github/workflows/run_on_push.yml --bind
   ```

## Visualisation des Résultats

Une fois les tests terminés :

1. Accédez à l'exécution du workflow dans l'onglet "Actions"
2. Faites défiler jusqu'à la section "Artifacts"
3. Téléchargez l'artefact "test-results"
4. Décompressez le fichier téléchargé
5. Ouvrez les fichiers HTML dans votre navigateur pour voir les rapports détaillés

Les rapports incluent :
- Rapports de couverture de code
- Résultats des tests end-to-end
- Logs d'exécution

## Compatibilité Pydantic

Le workflow `e2e_tests_pydantic_compat.yml` est spécialement conçu pour gérer les problèmes de compatibilité entre Pydantic v1 et v2. Il crée automatiquement une couche de compatibilité (`backend/utils/pydantic_compat.py`) qui permet d'utiliser les fonctionnalités de Pydantic v2 (comme `model_serializer` et `model_validator`) avec Pydantic v1.

Cette approche est particulièrement utile si vous utilisez Python 3.8 avec Pydantic v1, mais que votre code utilise des fonctionnalités de Pydantic v2.

## Limitations

- Les tests peuvent prendre plus de temps à s'exécuter que localement
- Les services externes (AcoustID et AudD) peuvent toujours rencontrer des problèmes de "Failed to convert features to audio" en raison des limitations de l'environnement
- GitHub Actions a une limite de temps d'exécution de 6 heures par workflow

## Dépannage

### Problèmes Courants

1. **Échec du démarrage des conteneurs** :
   - Vérifiez les logs dans l'étape "Build and start Docker containers"
   - Assurez-vous que le fichier `docker-compose.yml` est correctement configuré

2. **Échec des tests** :
   - Les tests sont configurés avec `continue-on-error: true`, donc le workflow continuera même si un test échoue
   - Consultez les rapports HTML pour voir les détails des échecs

3. **Problèmes d'API** :
   - Vérifiez que vos clés API sont correctement configurées dans les secrets GitHub
   - Assurez-vous que vos clés API sont valides et n'ont pas expiré

4. **Problèmes de compatibilité Pydantic** :
   - Si vous rencontrez des erreurs liées à Pydantic, utilisez le workflow `e2e_tests_pydantic_compat.yml`
   - Vérifiez que la couche de compatibilité est correctement créée et importée dans vos fichiers

5. **Le serveur backend ne démarre pas** :
   - Vérifiez les logs de l'étape "Start backend server"
   - Assurez-vous que les variables d'environnement sont correctement configurées
   - Augmentez le temps d'attente après le démarrage du serveur si nécessaire

### Obtenir de l'Aide

Si vous rencontrez des problèmes non couverts dans ce document, veuillez :

1. Vérifier les logs complets de l'exécution du workflow
2. Consulter la documentation des tests end-to-end dans `docs/tests/end_to_end_testing.md`
3. Ouvrir une issue sur GitHub avec les détails du problème
