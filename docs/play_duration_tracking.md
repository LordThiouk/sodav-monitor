# Système de Suivi de la Durée de Lecture

Ce document décrit le système de suivi de la durée de lecture implémenté dans le projet SODAV Monitor. Ce système permet de mesurer avec précision la durée de lecture des morceaux de musique sur les stations de radio, y compris en cas d'interruptions et de reprises.

## Objectifs

Le système de suivi de la durée de lecture a été conçu pour répondre aux exigences suivantes :

- Mesurer avec précision la durée de lecture des morceaux de musique
- Gérer les interruptions et les reprises de lecture
- Fusionner les détections lorsqu'un morceau est interrompu puis reprend dans un court laps de temps
- Enregistrer les données de durée de lecture dans la base de données
- Fournir des statistiques précises pour les rapports de diffusion

## Architecture

Le système de suivi de la durée de lecture est composé des éléments suivants :

### 1. PlayDurationTracker

La classe `PlayDurationTracker` est le cœur du système. Elle est responsable de :

- Démarrer le suivi de la durée de lecture lorsqu'un morceau est détecté
- Mettre à jour le suivi en continu
- Arrêter le suivi lorsque le morceau change ou que le silence est détecté
- Gérer les interruptions et les reprises
- Créer et mettre à jour les enregistrements de détection dans la base de données

### 2. Intégration avec TrackManager

La classe `TrackManager` a été modifiée pour utiliser le `PlayDurationTracker`. Elle :

- Initialise le tracker lors de sa création
- Délègue le suivi de la durée de lecture au tracker
- Fournit des méthodes pour démarrer, mettre à jour et arrêter le suivi
- Planifie le nettoyage périodique des pistes interrompues

### 3. Modifications du FingerprintHandler

La classe `FingerprintHandler` a été étendue pour :

- Récupérer l'empreinte digitale d'une piste à partir de la base de données
- Fournir cette empreinte au tracker pour le suivi des pistes

## Fonctionnement

### Démarrage du suivi

Lorsqu'un morceau est détecté sur une station, le système :

1. Récupère l'empreinte digitale du morceau
2. Démarre le suivi de la durée de lecture avec `PlayDurationTracker.start_tracking()`
3. Crée un enregistrement de détection dans la base de données avec `PlayDurationTracker.create_detection()`

### Détection des morceaux

Le système utilise plusieurs méthodes pour détecter les morceaux :

1. **Détection locale** : Recherche dans la base de données locale à l'aide des empreintes digitales
2. **Détection via AcoustID** : Utilise l'API AcoustID pour identifier les morceaux
   - L'empreinte digitale et la durée sont envoyées à l'API
   - La durée est convertie en entier et formatée en chaîne de caractères pour éviter les erreurs 400
   - Une validation est effectuée pour s'assurer que la durée est toujours valide (non nulle, positive)
3. **Détection via Audd.io** : Utilise l'API Audd.io comme méthode de secours
   - Les données audio brutes sont envoyées à l'API
   - Cette méthode est utilisée si AcoustID ne trouve pas de correspondance

Le système suit une hiérarchie de détection, passant à la méthode suivante si la précédente échoue, assurant ainsi une détection robuste même en cas d'échec d'une API spécifique.

### Mise à jour du suivi

Pendant la lecture du morceau, le système :

1. Met à jour régulièrement le suivi avec `PlayDurationTracker.update_tracking()`
2. Enregistre l'heure de la dernière mise à jour

### Arrêt du suivi

Lorsque le morceau change ou que le silence est détecté, le système :

1. Arrête le suivi avec `PlayDurationTracker.stop_tracking()`
2. Calcule la durée totale de lecture
3. Met à jour l'enregistrement de détection dans la base de données

### Gestion des interruptions

Lorsqu'un morceau est interrompu (par exemple, par une publicité), le système :

1. Arrête le suivi avec `is_silence=True`
2. Conserve les informations de la piste dans `interrupted_tracks`
3. Si le même morceau reprend dans un court laps de temps, le système :
   - Reprend le suivi à partir de l'état précédent
   - Met à jour l'enregistrement de détection existant
   - Accumule la durée de lecture

### Nettoyage des pistes interrompues

Périodiquement, le système :

1. Nettoie les pistes interrompues trop anciennes avec `PlayDurationTracker.cleanup_interrupted_tracks()`
2. Finalise les enregistrements de détection pour ces pistes

## Tests

Le système est testé par plusieurs suites de tests :

1. `test_play_duration_tracker.py` : Tests unitaires pour le `PlayDurationTracker`
2. `test_enhanced_radio_simulator.py` : Tests d'intégration avec le simulateur de radio amélioré
3. `test_play_duration.py` : Tests d'intégration pour le suivi de la durée de lecture
4. `test_play_duration_real_data.py` : Tests avec des données réelles

Ces tests vérifient :

- Le démarrage, la mise à jour et l'arrêt du suivi
- La création et la mise à jour des enregistrements de détection
- La gestion des interruptions et des reprises
- La précision de la durée de lecture mesurée

## Exécution des tests

Pour exécuter tous les tests liés à la durée de lecture, utilisez le script `run_play_duration_tests.py` :

```bash
python -m backend.tests.utils.run_play_duration_tests
```

## Améliorations futures

Voici quelques améliorations qui pourraient être apportées au système :

1. **Optimisation des performances** : Réduire l'utilisation des ressources pour les systèmes avec de nombreuses stations
2. **Amélioration de la détection des interruptions** : Utiliser des algorithmes plus avancés pour détecter les interruptions
3. **Intégration avec d'autres systèmes** : Connecter le système à d'autres sources de données pour améliorer la précision
4. **Interface utilisateur** : Ajouter une interface pour visualiser en temps réel les pistes en cours de lecture et leur durée
5. **Rapports améliorés** : Générer des rapports plus détaillés sur la durée de lecture des morceaux
6. **Diversification des méthodes de détection** : Ajouter d'autres services de détection pour améliorer la robustesse
7. **Système de fallback amélioré** : Implémenter un système de retry avec backoff exponentiel pour les requêtes API qui échouent
8. **Enrichissement de la base de données locale** : Développer un système d'apprentissage qui enrichit progressivement la base de données locale avec les résultats des API externes

## Résolution des problèmes courants

### Erreur "missing required parameter 'duration'" avec AcoustID

Cette erreur peut se produire lorsque le paramètre "duration" n'est pas correctement formaté ou est manquant dans les requêtes à l'API AcoustID. Pour résoudre ce problème :

1. Assurez-vous que la durée est toujours convertie en entier puis en chaîne de caractères : `str(int(float(duration)))`
2. Vérifiez que la durée est valide (non nulle, positive) avant d'envoyer la requête
3. Utilisez une valeur par défaut (par exemple, 30 secondes) si la durée est invalide
4. Activez la journalisation détaillée pour voir les paramètres exacts envoyés à l'API

Ces corrections ont été implémentées dans les fichiers `real_api_detection_test.py` et `external_detection.py` pour assurer un fonctionnement fiable de l'API AcoustID. 