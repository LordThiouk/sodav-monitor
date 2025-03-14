# Tests

Ce dossier contient la documentation relative aux tests du projet SODAV Monitor.

## Stratégie de Test

- **testing_strategy.md** : Documentation détaillée sur la stratégie de test
- **test_coverage.md** : Objectifs et mesures de couverture de test

## Tests Unitaires

- **unit_testing_guide.md** : Guide pour écrire des tests unitaires
- **isrc_uniqueness_test.md** : Tests pour la contrainte d'unicité ISRC

## Tests d'Intégration

- **integration_testing.md** : Documentation spécifique pour les tests d'intégration
- **api_integration_tests.md** : Tests d'intégration pour les API

## Tests de Détection

- **detection_testing_guide.md** : Guide pour tester le système de détection
- **test_acoustid_detection.md** : Tests pour la détection via AcoustID
- **test_audd_detection.md** : Tests pour la détection via AudD

## Tests de Détection Musicale

Le système de détection musicale est un composant central de SODAV Monitor. Nous avons créé plusieurs guides pour tester les différentes parties de ce système :

- [Test de Détection AcoustID](test_acoustid_detection.md) - Guide pour tester la détection musicale avec l'API AcoustID
- [Test de Détection AudD](test_audd_detection.md) - Guide pour tester la détection musicale avec l'API AudD

## Optimisations Récentes

### Résolution du Problème d'Erreur 413 avec AcoustID

Nous avons récemment résolu un problème où l'API AcoustID renvoyait une erreur 413 (Request Entity Too Large) lors de l'envoi d'empreintes digitales. La solution a été de modifier la méthode HTTP utilisée de GET à POST, ce qui permet d'envoyer des empreintes plus longues sans limitations de taille.

Pour plus de détails, consultez le [guide de test AcoustID](test_acoustid_detection.md).

## Comment Exécuter les Tests

Pour exécuter les tests, suivez les instructions dans les guides spécifiques. En général, vous pouvez exécuter un script de test avec la commande suivante depuis la racine du projet :

```bash
python backend/scripts/detection/<nom_du_script>.py
```

## Prérequis pour les Tests

1. Assurez-vous que toutes les clés API nécessaires sont configurées dans le fichier `.env` :
   - `ACOUSTID_API_KEY` pour AcoustID
   - `AUDD_API_KEY` pour AudD

2. Vérifiez que l'outil `fpcalc` est correctement installé dans `backend/bin/`

3. Assurez-vous que les fichiers audio de test sont disponibles dans `backend/tests/data/audio/`

## Résolution des Problèmes Courants

Si vous rencontrez des problèmes lors de l'exécution des tests, consultez les guides spécifiques pour des solutions détaillées. Voici quelques problèmes courants :

- **Erreur 413 avec AcoustID** - Vérifiez que la modification pour utiliser POST est bien appliquée
- **fpcalc non trouvé** - Assurez-vous que l'outil est correctement installé dans `backend/bin/`
- **Clés API invalides** - Vérifiez que les clés sont correctement configurées dans le fichier `.env`
- **Fichiers audio non reconnus** - Essayez avec des fichiers audio plus longs ou plus connus
