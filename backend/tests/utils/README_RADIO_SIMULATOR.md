# Guide d'Utilisation du Simulateur de Radio pour SODAV Monitor

Ce guide explique comment utiliser le simulateur de radio amélioré pour tester le système de détection musicale SODAV Monitor en conditions réelles.

## 1. Vue d'ensemble

Le simulateur de radio est un outil qui permet de :

- Diffuser des flux audio en continu via HTTP
- Simuler plusieurs stations de radio avec des playlists personnalisées
- Enregistrer avec précision les durées de lecture
- Simuler des interruptions de flux
- Tester la détection musicale avec de vrais appels API
- Générer des logs détaillés pour analyse

## 2. Composants du Simulateur

Le système comprend plusieurs composants :

- **RadioSimulator** : Simulateur de base qui diffuse des fichiers audio
- **EnhancedRadioSimulator** : Version améliorée avec fonctionnalités supplémentaires
- **Scripts de test** : Pour tester la détection musicale avec différentes approches

## 3. Installation et Prérequis

### Prérequis

- Python 3.8+
- Bibliothèques : pydub, requests, etc.
- Fichiers audio MP3 dans le répertoire `backend/tests/data/audio/senegal`
- `fpcalc.exe` dans le répertoire `backend/bin/` (pour la génération d'empreintes acoustiques)

### Préparation des fichiers audio

Pour copier des fichiers audio depuis votre dossier Téléchargements :

```bash
cd backend
python -m tests.utils.copy_downloaded_audio
```

## 4. Utilisation du Simulateur de Radio

### Simulateur de Radio Simple

```python
from backend.tests.utils.radio_simulator import RadioSimulator

# Créer le simulateur
simulator = RadioSimulator()

# Créer une station
station = simulator.create_station("Radio Dakar", audio_dir="chemin/vers/audio")

# Démarrer la station
station.start()

# URL de streaming : http://localhost:8765
```

### Simulateur de Radio Amélioré

```python
from backend.tests.utils.enhanced_radio_simulator import EnhancedRadioSimulator

# Créer le simulateur amélioré
simulator = EnhancedRadioSimulator()

# Créer une station avec métadonnées
station = simulator.create_station(
    name="Radio Sénégal",
    audio_dir="chemin/vers/audio",
    genre="Hip-Hop/Rap",
    country="Sénégal",
    language="Wolof/Français"
)

# Démarrer l'enregistrement des logs
simulator.start_logging()

# Démarrer la station
station.start()

# Démarrer le monitoring
simulator.start_monitoring(interval_seconds=5)

# Simuler une interruption
simulator.simulate_interruption("Radio Sénégal", duration_seconds=5)

# Sélectionner manuellement un morceau
simulator.select_track("Radio Sénégal", track_index=0)

# Exporter les logs
simulator.export_logs("logs.json", format="json")

# Arrêter la station
station.stop()

# Arrêter le monitoring et l'enregistrement des logs
simulator.stop_monitoring()
simulator.stop_logging()
```

## 5. Tests de Détection Musicale

### Test avec Simulateur Simple

```bash
cd backend
python -m tests.utils.senegal_radio_simulator
```

### Test avec Simulateur Amélioré

```bash
cd backend
python -m tests.utils.run_senegal_radio_enhanced
```

### Test avec Vrais Appels API

```bash
cd backend
python -m tests.utils.run_real_api_detection
```

Ce test utilise la hiérarchie de détection complète :
1. Détection locale
2. MusicBrainz/AcoustID
3. Audd.io

## 6. Fonctionnalités Avancées

### Enregistrement des Détections

Le simulateur peut enregistrer les détections avec :

```python
simulator.register_detection(
    station_name="Radio Sénégal",
    track_name="Nom du morceau",
    detection_method="local",  # ou "musicbrainz", "audd"
    confidence=0.95,
    detected_at=datetime.now(),
    play_duration=30.0,
    fingerprint="empreinte_acoustique",
    metadata={"artist": "Nom de l'artiste"}
)
```

### Analyse des Logs

Les logs exportés contiennent :

- **play_logs** : Événements de lecture (début/fin de morceau, interruptions)
- **detection_logs** : Détections enregistrées

Exemple de format JSON :
```json
{
  "play_logs": [
    {
      "station_name": "Radio Sénégal",
      "event_type": "track_start",
      "track_name": "morceau.mp3",
      "timestamp": "2023-03-14T12:30:45",
      "duration": 0,
      "details": {}
    }
  ],
  "detection_logs": [
    {
      "station_name": "Radio Sénégal",
      "track_name": "Morceau détecté",
      "detection_method": "musicbrainz",
      "confidence": 0.95,
      "detected_at": "2023-03-14T12:31:15",
      "play_duration": 30.5,
      "fingerprint": "...",
      "metadata": {"artist": "Artiste"}
    }
  ]
}
```

### Calcul des Durées de Lecture

Pour obtenir la durée totale de lecture :

```python
# Durée totale pour toutes les stations
total_duration = simulator.get_total_play_duration()

# Durée pour une station spécifique
station_duration = simulator.get_total_play_duration(station_name="Radio Sénégal")

# Durée pour un morceau spécifique
track_duration = simulator.get_total_play_duration(track_name="morceau.mp3")
```

## 7. Dépannage

### Problèmes courants

1. **Aucun fichier audio trouvé** :
   - Utilisez `copy_downloaded_audio.py` pour copier des fichiers depuis votre dossier Téléchargements

2. **fpcalc.exe non trouvé** :
   - Vérifiez que `fpcalc.exe` est présent dans `backend/bin/`
   - Téléchargez-le depuis [Acoustid](https://acoustid.org/chromaprint) si nécessaire

3. **Clés API manquantes** :
   - Pour les tests avec API réelles, configurez les variables d'environnement :
     - `ACOUSTID_API_KEY` pour MusicBrainz
     - `AUDD_API_KEY` pour Audd.io

4. **Erreurs de port** :
   - Si un port est déjà utilisé, modifiez-le dans la création de la station

## 8. Exemples d'Utilisation

### Exemple 1 : Test simple avec une station

```python
from backend.tests.utils.enhanced_radio_simulator import EnhancedRadioSimulator
import time

simulator = EnhancedRadioSimulator()
station = simulator.create_station("Test Station", audio_dir="chemin/vers/audio")
station.start()

# Laisser la station diffuser pendant 60 secondes
time.sleep(60)

station.stop()
```

### Exemple 2 : Test complet avec détection

```python
# Voir le script run_real_api_detection.py pour un exemple complet
```

## 9. Ressources Additionnelles

- Documentation de l'API MusicBrainz : [AcoustID API](https://acoustid.org/webservice)
- Documentation de l'API Audd.io : [Audd.io API](https://docs.audd.io/)
- Outils de génération d'empreintes acoustiques : [Chromaprint](https://acoustid.org/chromaprint)

## 10. Contribution

Pour améliorer le simulateur :

1. Ajoutez de nouveaux formats audio supportés
2. Implémentez des méthodes de détection supplémentaires
3. Améliorez la précision du calcul des durées de lecture
4. Ajoutez des visualisations pour les résultats de détection 

## Test Multi-Stations

Le système SODAV Monitor inclut maintenant un test avancé qui permet de simuler plusieurs stations de radio simultanément et de tester la détection musicale en parallèle sur toutes ces stations.

### Fonctionnalités du Test Multi-Stations

- Création et gestion de plusieurs stations de radio virtuelles simultanées
- Détection musicale en parallèle sur toutes les stations
- Simulation d'interruptions sur des stations spécifiques
- Sélection manuelle de pistes sur des stations spécifiques
- Génération de rapports détaillés sur les détections et les durées de lecture
- Support pour différents formats audio (MP3, WAV, FLAC, etc.)
- Intégration avec les API de détection musicale (locale, MusicBrainz, Audd.io)

### Exécution du Test Multi-Stations

Pour exécuter le test multi-stations, utilisez la commande suivante depuis le répertoire racine du projet :

```bash
cd backend
python -m tests.utils.run_multi_station_test
```

Vous pouvez également spécifier des options supplémentaires :

```bash
python -m tests.utils.run_multi_station_test --acoustid-key VOTRE_CLE --audd-key VOTRE_CLE --stations 4 --detections 3 --duration 20
```

Options disponibles :
- `--acoustid-key` : Clé API AcoustID
- `--audd-key` : Clé API Audd.io
- `--stations` : Nombre de stations à simuler (défaut: 3)
- `--detections` : Nombre de détections par station (défaut: 2)
- `--duration` : Durée de chaque détection en secondes (défaut: 15)
- `--no-interruption` : Désactiver la simulation d'interruption
- `--no-manual-selection` : Désactiver la sélection manuelle de piste

### Structure du Test Multi-Stations

Le test multi-stations est composé de deux scripts principaux :

1. `multi_station_test.py` : Implémente la logique du test multi-stations
2. `run_multi_station_test.py` : Script d'exécution qui facilite le lancement du test

Le test suit les étapes suivantes :

1. Vérification des fichiers audio disponibles
2. Configuration des clés API nécessaires
3. Création de plusieurs stations de radio virtuelles
4. Démarrage de toutes les stations
5. Exécution des détections en parallèle sur toutes les stations
6. Simulation d'interruptions et de sélections manuelles de pistes
7. Génération d'un rapport détaillé sur les détections et les durées de lecture
8. Exportation des logs au format JSON

### Exemple de Rapport

À la fin du test, un rapport détaillé est généré, incluant :

- Nombre total de détections
- Méthodes de détection utilisées
- Détections par station
- Durée totale de lecture enregistrée

Les logs sont exportés dans un fichier JSON nommé `multi_station_test_YYYYMMDD_HHMMSS.json`.

### Intégration avec le Système de Détection

Le test multi-stations s'intègre parfaitement avec le système de détection musicale existant, utilisant la hiérarchie de détection suivante :

1. Détection locale (empreintes acoustiques)
2. MusicBrainz API
3. Audd.io API

Chaque détection est enregistrée avec des métadonnées détaillées, incluant la méthode utilisée, le niveau de confiance, et la durée de lecture. 