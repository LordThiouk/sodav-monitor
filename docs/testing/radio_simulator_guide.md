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
- **Scripts de test** : Outils pour tester la détection musicale avec le simulateur

## 3. Installation et Prérequis

### Prérequis

- Python 3.8+
- Fichiers audio MP3 dans le répertoire `backend/tests/data/audio/senegal`
- `fpcalc.exe` dans le répertoire `backend/bin/` (pour la génération d'empreintes acoustiques)

### Installation

1. Assurez-vous que les dépendances Python sont installées :
   ```bash
   pip install -r requirements.txt
   ```

2. Préparez les fichiers audio pour les tests :
   ```bash
   python -m backend.tests.utils.copy_downloaded_audio
   ```
   Ou téléchargez des fichiers audio de test :
   ```bash
   python -m backend.tests.utils.download_test_audio_direct
   ```

## 4. Utilisation du Simulateur Simple

Le simulateur de radio simple permet de diffuser des fichiers audio via HTTP :

```python
from backend.tests.utils.radio_simulator import RadioSimulator

# Créer un simulateur
simulator = RadioSimulator()

# Créer une station
station = simulator.create_station(
    name="Radio Sénégal",
    audio_dir="backend/tests/data/audio/senegal"
)

# Démarrer la station
station.start()

# Obtenir l'URL de streaming
stream_url = f"http://localhost:{station.port}"
print(f"URL de streaming: {stream_url}")

# Arrêter la station
station.stop()
```

Pour exécuter le simulateur simple directement :
```bash
python -m backend.tests.utils.senegal_radio_simulator
```

## 5. Utilisation du Simulateur Amélioré

Le simulateur amélioré offre des fonctionnalités supplémentaires :

```python
from backend.tests.utils.enhanced_radio_simulator import EnhancedRadioSimulator

# Créer un simulateur amélioré
simulator = EnhancedRadioSimulator()

# Créer une station avec métadonnées
station = simulator.create_station(
    name="Radio Sénégal",
    audio_dir="backend/tests/data/audio/senegal",
    genre="Hip-Hop/Rap",
    country="Sénégal",
    language="Wolof/Français"
)

# Démarrer l'enregistrement des logs
simulator.start_logging()

# Démarrer la station
station.start()

# Démarrer le monitoring
simulator.start_monitoring()

# Simuler une interruption
simulator.simulate_interruption("Radio Sénégal", duration_seconds=5)

# Sélectionner manuellement un morceau
simulator.select_track("Radio Sénégal", track_index=0)

# Obtenir les logs de lecture
play_logs = simulator.get_play_logs()

# Calculer la durée totale de lecture
total_duration = simulator.get_total_play_duration(station_name="Radio Sénégal")

# Exporter les logs
simulator.export_logs("logs.json", format="json")

# Arrêter le monitoring
simulator.stop_monitoring()

# Arrêter la station
station.stop()

# Arrêter l'enregistrement des logs
simulator.stop_logging()
```

Pour exécuter le simulateur amélioré directement :
```bash
python -m backend.tests.utils.run_senegal_radio_enhanced
```

## 6. Test de Détection Musicale

### Test Simple

Pour tester la détection musicale avec le simulateur simple :
```bash
python -m backend.tests.utils.simple_detection_test
```

Ce script :
1. Crée une station de radio simulée
2. Diffuse des fichiers audio
3. Capture l'audio du flux
4. Effectue une détection musicale simulée
5. Enregistre les résultats

### Test avec API Réelles

Pour tester la détection musicale avec de vrais appels API :
```bash
python -m backend.tests.utils.run_real_api_detection
```

Ce script utilise la hiérarchie de détection suivante :
1. Détection locale (empreintes acoustiques)
2. MusicBrainz API
3. Audd.io API

### Test Multi-Stations

Pour tester la détection musicale avec plusieurs stations simultanées :
```bash
python -m backend.tests.utils.run_multi_station_test
```

Options disponibles :
- `--acoustid-key` : Clé API AcoustID
- `--audd-key` : Clé API Audd.io
- `--stations` : Nombre de stations à simuler (défaut: 3)
- `--detections` : Nombre de détections par station (défaut: 2)
- `--duration` : Durée de chaque détection en secondes (défaut: 15)
- `--no-interruption` : Désactiver la simulation d'interruption
- `--no-manual-selection` : Désactiver la sélection manuelle de piste

## 7. Structure des Logs

Les logs générés contiennent des informations détaillées sur :

- Les événements de lecture (début/fin de morceau)
- Les interruptions simulées
- Les détections musicales
- Les correspondances trouvées

Format des logs :
```json
{
  "play_logs": [
    {
      "timestamp": "2023-03-14T12:30:45",
      "station_name": "Radio Sénégal",
      "event_type": "track_start",
      "track_name": "DIP DOUNDOU GUISS - CALIFAT",
      "duration": 0,
      "details": {}
    },
    ...
  ],
  "detection_logs": [
    {
      "timestamp": "2023-03-14T12:31:15",
      "station_name": "Radio Sénégal Test",
      "track_name": "DIP DOUNDOU GUISS - CALIFAT",
      "detection_method": "fingerprint",
      "confidence": 0.95,
      "play_duration": 30.5,
      "fingerprint": "...",
      "metadata": {"detection_index": 1}
    },
    ...
  ]
}
```

## 8. Mesure de la Précision

Le simulateur permet de mesurer la précision de la détection en comparant :

- Les morceaux réellement diffusés (logs de lecture)
- Les morceaux détectés (logs de détection)
- Les durées de lecture réelles vs. détectées

Métriques calculées :
- Taux de détection correct
- Précision des durées de lecture
- Temps de réponse de la détection

## 9. Conseils et Bonnes Pratiques

1. **Préparation des fichiers audio** :
   - Utilisez des fichiers MP3 de bonne qualité
   - Assurez-vous que les fichiers ont des métadonnées correctes
   - Organisez les fichiers par genre ou région

2. **Configuration des API** :
   - Obtenez des clés API pour AcoustID et Audd.io
   - Définissez les variables d'environnement `ACOUSTID_API_KEY` et `AUDD_API_KEY`
   - Respectez les limites de requêtes des API

3. **Optimisation des tests** :
   - Commencez par des tests simples avant de passer aux tests multi-stations
   - Utilisez des durées de détection plus courtes pour les tests initiaux
   - Augmentez progressivement la complexité des tests

4. **Analyse des résultats** :
   - Examinez les logs pour identifier les problèmes de détection
   - Comparez les résultats avec différentes méthodes de détection
   - Utilisez les métriques pour améliorer l'algorithme de détection

## 10. Dépannage

### Problèmes courants

1. **Aucun fichier audio trouvé** :
   - Vérifiez que les fichiers audio sont présents dans le répertoire `backend/tests/data/audio/senegal`
   - Utilisez le script `copy_downloaded_audio.py` pour copier des fichiers depuis le dossier Téléchargements

2. **Erreur de génération d'empreintes acoustiques** :
   - Vérifiez que `fpcalc.exe` est présent dans le répertoire `backend/bin/`
   - Assurez-vous que la variable d'environnement `FPCALC_PATH` est correctement définie

3. **Échec des appels API** :
   - Vérifiez que les clés API sont correctement configurées
   - Assurez-vous que vous avez une connexion Internet active
   - Vérifiez les limites de requêtes des API

4. **Problèmes de détection** :
   - Augmentez la durée de détection pour améliorer la précision
   - Vérifiez la qualité des fichiers audio
   - Essayez différentes méthodes de détection 