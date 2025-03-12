# Exécution des Tests End-to-End avec GitHub Actions

Ce document explique comment utiliser GitHub Actions pour exécuter les tests end-to-end du système SODAV Monitor sans avoir besoin d'installer Docker localement.

## Avantages de l'utilisation de GitHub Actions

- Aucune installation locale requise
- Exécution dans un environnement isolé et propre
- Ressources de calcul fournies par GitHub
- Résultats des tests facilement accessibles
- Intégration avec le système de CI/CD

## Configuration

Le workflow GitHub Actions pour les tests end-to-end est défini dans le fichier `.github/workflows/e2e_tests_docker.yml`. Ce workflow :

1. Démarre les conteneurs Docker nécessaires
2. Installe les dépendances requises
3. Exécute les tests end-to-end
4. Génère des rapports HTML
5. Télécharge les rapports comme artefacts

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
2. Sélectionnez le workflow "End-to-End Tests in Docker" dans la barre latérale
3. Cliquez sur le bouton "Run workflow"
4. Sélectionnez la branche sur laquelle exécuter les tests
5. Cliquez sur "Run workflow"

### Exécution Automatique

Le workflow est également configuré pour s'exécuter automatiquement :
- Chaque lundi à minuit (UTC)

## Visualisation des Résultats

Une fois les tests terminés :

1. Accédez à l'exécution du workflow dans l'onglet "Actions"
2. Faites défiler jusqu'à la section "Artifacts"
3. Téléchargez l'artefact "e2e-test-reports"
4. Décompressez le fichier téléchargé
5. Ouvrez les fichiers HTML dans votre navigateur pour voir les rapports détaillés

Les rapports incluent :
- `detection_workflow_report.html` : Résultats du test de workflow de détection
- `report_generation_report.html` : Résultats du test de génération de rapport
- `play_duration_report.html` : Résultats du test de précision de durée de lecture
- `end_to_end_workflow_report.html` : Résultats du test de workflow end-to-end

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

### Obtenir de l'Aide

Si vous rencontrez des problèmes non couverts dans ce document, veuillez :

1. Vérifier les logs complets de l'exécution du workflow
2. Consulter la documentation des tests end-to-end dans `docs/tests/end_to_end_testing.md`
3. Ouvrir une issue sur GitHub avec les détails du problème 