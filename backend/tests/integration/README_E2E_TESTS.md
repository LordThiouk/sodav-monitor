# End-to-End (E2E) Testing for SODAV Monitor

Ce document décrit l'approche de test end-to-end pour le système SODAV Monitor, y compris comment exécuter les tests et ce qu'ils vérifient.

## Vue d'ensemble

Les tests end-to-end vérifient que l'ensemble du système fonctionne correctement dans des conditions réelles. Ces tests couvrent le flux de travail complet, de la capture audio à la génération de rapports, en s'assurant que tous les composants fonctionnent ensemble de manière transparente.

## Règles de test E2E

Nos tests E2E suivent un ensemble de règles strictes pour garantir une couverture complète :

### 1. Principes généraux
- Tester le système entier (frontend, backend, base de données, API, intégrations externes)
- Utiliser des scénarios du monde réel
- Automatiser les tests autant que possible
- Surveiller les performances
- Assurer la cohérence des données

### 2. Workflow de détection
- Vérifier si c'est de la parole ou de la musique
- Effectuer d'abord une détection locale
- Utiliser l'API MusicBrainz si nécessaire
- Utiliser l'API Audd.io en dernier recours
- Enregistrer les détails de détection

### 3. Précision de la durée de lecture
- Enregistrer l'horodatage de début
- Enregistrer l'horodatage de fin
- Calculer la durée exacte de lecture
- Valider la durée de lecture selon les règles

### 4. Validation des stations et des flux
- Tester les flux radio en direct
- Vérifier les métadonnées des stations
- Tester les mécanismes de récupération

### 5. Génération de rapports
- Vérifier le contenu des rapports
- Tester les rapports d'abonnement
- Vérifier la précision des données

### 6. Performance et évolutivité
- Tester la charge du système
- Tester le traitement de grands ensembles de données

### 7. Cohérence de la base de données
- Éviter les détections en double
- Assurer les relations de clés étrangères
- Préserver les données historiques

## Couverture des tests

Les tests E2E couvrent les aspects suivants du système :

1. **Workflow de détection** : Teste le processus complet de détection, de la capture audio au stockage en base de données
2. **Précision de la durée de lecture** : Vérifie que la durée de lecture est correctement calculée et stockée
3. **Streaming des stations** : Teste les métadonnées des stations et la stabilité des flux
4. **Génération de rapports** : Vérifie que les rapports contiennent des données précises
5. **Performance et évolutivité** : Teste les performances du système sous charge
6. **Cohérence de la base de données** : Assure l'intégrité des données et les relations appropriées
7. **Workflow de bout en bout** : Teste le flux de travail complet, de la capture audio à la génération de rapports

## Prérequis

Pour exécuter les tests E2E, vous avez besoin de :

1. Python 3.8 ou supérieur
2. Base de données PostgreSQL (ou SQLite pour les tests locaux)
3. Serveur Redis (pour le cache)
4. Connexion Internet (pour accéder aux flux radio)
5. Packages Python requis (voir requirements.txt)

## Exécution des tests

### 1. Configuration de l'environnement

```bash
# Créer et activer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Exécuter les tests

```bash
# Exécuter tous les tests E2E
python -m pytest backend/tests/integration/test_end_to_end.py -v

# Exécuter un test E2E spécifique
python -m pytest backend/tests/integration/test_end_to_end.py::TestEndToEnd::test_detection_workflow -v

# Exécuter avec sortie de logs détaillée
python -m pytest backend/tests/integration/test_end_to_end.py -vv --log-cli-level=DEBUG
```

### 3. Tests dans la nouvelle structure

Avec la nouvelle organisation des tests, les tests E2E sont maintenant dans le dossier `integration/`. Pour les exécuter :

```bash
# Exécuter tous les tests d'intégration
python -m pytest backend/tests/integration/ -v

# Exécuter uniquement les tests E2E
python -m pytest backend/tests/integration/test_end_to_end.py -v
```

## Dépannage

Si les tests échouent, vérifiez les points suivants :

1. **Connexion Internet** : Les tests E2E nécessitent une connexion Internet stable pour accéder aux flux radio.
2. **Services externes** : Les services externes (MusicBrainz, Audd.io) peuvent être indisponibles ou limiter les requêtes.
3. **Base de données** : Assurez-vous que la base de données est accessible et que les migrations sont à jour.
4. **Redis** : Vérifiez que le serveur Redis est en cours d'exécution.
5. **Logs** : Consultez les logs pour des informations détaillées sur les erreurs.

Pour des informations de débogage détaillées, exécutez les tests avec un niveau de log plus élevé :

```bash
python -m pytest backend/tests/integration/test_end_to_end.py -vv --log-cli-level=DEBUG
```

## Extending the Tests

To add new E2E tests:

1. Add new test methods to the `TestEndToEnd` class in `test_end_to_end.py`
2. Follow the existing pattern of:
   - Setting up test data
   - Performing actions
   - Verifying results
   - Handling failure cases gracefully
3. Use the `@pytest.mark.asyncio` decorator for async tests
4. Add appropriate assertions to verify expected behavior

## Integration with CI/CD

These tests can be integrated into a CI/CD pipeline to ensure system quality:

1. Run tests automatically on each commit
2. Set appropriate timeouts for long-running tests
3. Configure the pipeline to use test databases
4. Generate test reports for review
5. **Note**: Expect and accept "Failed to convert features to audio" errors in CI/CD environments

## Conclusion

The E2E tests provide comprehensive validation of the SODAV Monitor system under real-world conditions. By running these tests regularly, we can ensure that the system continues to function correctly as changes are made. The tests are designed to be resilient to real-world variations in radio streams and music content, making them reliable indicators of system health.

While some components like external detection services cannot be fully tested in all environments, the tests are designed to handle these limitations gracefully and still provide valuable validation of the overall system functionality.
