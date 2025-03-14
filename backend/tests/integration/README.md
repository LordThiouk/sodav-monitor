# Tests d'Intégration pour SODAV Monitor

Ce répertoire contient les tests d'intégration pour le système SODAV Monitor, qui vérifient que les différents composants du système fonctionnent correctement ensemble.

## Structure des Tests d'Intégration

- `test_radio_simulation.py` : Tests de détection musicale avec des stations de radio simulées
- `test_play_duration.py` : Tests spécifiques pour la précision de la durée de lecture
- `detection/` : Tests d'intégration pour les composants de détection
- `analytics/` : Tests d'intégration pour les composants d'analyse

## Prérequis pour l'Exécution des Tests

1. **Fichiers Audio de Test** : Les tests nécessitent des fichiers audio MP3 dans le répertoire `backend/tests/data/audio/senegal/`. Si aucun fichier n'est présent, les tests seront ignorés.

2. **Variables d'Environnement** : Pour tester les services externes, les variables d'environnement suivantes doivent être définies :
   - `ACOUSTID_API_KEY` : Clé API pour AcoustID
   - `AUDD_API_KEY` : Clé API pour AudD

3. **Dépendances** : Assurez-vous que toutes les dépendances sont installées :
   ```bash
   pip install -r requirements.txt
   ```

## Exécution des Tests

### Exécuter tous les tests d'intégration
```bash
python -m pytest backend/tests/integration/
```

### Exécuter un test spécifique
```bash
python -m pytest backend/tests/integration/test_radio_simulation.py
```

### Exécuter une méthode de test spécifique
```bash
python -m pytest backend/tests/integration/test_radio_simulation.py::TestRadioSimulation::test_detection_with_simulated_radio
```

### Exécuter les tests avec plus de détails
```bash
python -m pytest backend/tests/integration/test_radio_simulation.py -v
```

### Exécuter les tests avec affichage des logs
```bash
python -m pytest backend/tests/integration/test_radio_simulation.py -v --log-cli-level=INFO
```

## Préparation des Fichiers Audio de Test

Si vous n'avez pas de fichiers audio de test, vous pouvez :

1. **Utiliser le script de génération** :
   ```bash
   python backend/tests/utils/generate_test_audio.py
   ```

2. **Copier des fichiers existants** :
   ```bash
   python backend/tests/utils/copy_test_audio.py
   ```

3. **Télécharger des fichiers de test** (si les URLs sont configurées) :
   ```bash
   python backend/tests/utils/download_test_audio.py
   ```

## Bonnes Pratiques pour les Tests d'Intégration

1. **Isolation** : Chaque test doit être indépendant et ne pas dépendre de l'état laissé par d'autres tests.

2. **Fixtures réutilisables** : Utiliser des fixtures pytest pour partager la configuration entre les tests.

3. **Nettoyage** : Toujours nettoyer les ressources (stations, connexions) après les tests, même en cas d'erreur.

4. **Logging** : Utiliser des logs détaillés pour faciliter le débogage des tests qui échouent.

5. **Skip vs Fail** : Utiliser `pytest.skip()` pour les conditions qui ne sont pas des erreurs (comme l'absence de fichiers audio) et réserver les assertions pour les véritables erreurs.

6. **Timeouts** : Toujours implémenter des timeouts pour éviter que les tests ne se bloquent indéfiniment.

7. **Données de test** : Utiliser des données de test réalistes mais contrôlées pour des résultats reproductibles.

## Gestion des Cas Particuliers

Les tests sont conçus pour gérer les cas particuliers suivants :

1. **Absence de fichiers audio** : Les tests sont ignorés avec un message explicatif.

2. **Contenu non musical** : Si l'audio capturé n'est pas musical (parole ou silence), le test est ignoré.

3. **Services externes indisponibles** : Si les services externes ne sont pas disponibles, le test est ignoré.

4. **Erreurs de capture audio** : Les erreurs lors de la capture audio sont gérées et loguées.

## Documentation des Tests

Pour plus d'informations sur la conformité des tests avec les règles établies, consultez le fichier `E2E_COMPLIANCE.md` dans ce répertoire.

## Contribution aux Tests

Lorsque vous ajoutez de nouveaux tests d'intégration, assurez-vous de :

1. Suivre les conventions de nommage existantes
2. Documenter clairement le but du test
3. Gérer correctement les ressources (création et nettoyage)
4. Gérer les cas d'erreur et les conditions particulières
5. Ajouter des logs appropriés pour faciliter le débogage
