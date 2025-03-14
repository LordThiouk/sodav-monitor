# Détection de morceaux à partir des données de station

## Introduction

Ce document explique comment utiliser la fonctionnalité de détection de morceaux à partir des données audio des stations radio dans le système SODAV Monitor. Cette fonctionnalité permet d'identifier les morceaux joués en temps réel sur les stations radio.

## Flux de travail

Le processus de détection à partir des données de station fonctionne comme suit :

1. **Capture des données audio** : Le système capture les données audio de la station radio.
2. **Traitement des données** : Les données audio sont traitées pour extraire les caractéristiques nécessaires à la détection.
3. **Détection locale** : Le système tente d'abord de trouver une correspondance dans la base de données locale.
4. **Détection externe** : Si aucune correspondance locale n'est trouvée, le système utilise des services externes comme AcoustID pour identifier le morceau.
5. **Enregistrement des résultats** : Les résultats de la détection sont enregistrés dans la base de données.

## Utilisation via l'API

### Endpoint de détection

```
POST /api/detection/detect-from-station
```

### Paramètres

- `station_id` (obligatoire) : ID de la station radio
- `audio_file` (obligatoire) : Fichier audio à analyser
- `station_name` (optionnel) : Nom de la station radio

### Exemple de requête

```bash
curl -X POST "http://localhost:8000/api/detection/detect-from-station" \
  -H "Content-Type: multipart/form-data" \
  -F "station_id=1" \
  -F "station_name=Radio Sénégal" \
  -F "audio_file=@/chemin/vers/fichier.mp3"
```

### Exemple de réponse

```json
{
  "success": true,
  "detection": {
    "title": "Titre du morceau",
    "artist": "Nom de l'artiste",
    "album": "Nom de l'album",
    "confidence": 0.95,
    "detection_id": 123,
    "track_id": 456,
    "station_id": 1,
    "detected_at": "2023-05-01T12:34:56.789Z"
  },
  "source": "acoustid"
}
```

## Utilisation via le script de test

Un script de test est disponible pour tester la détection à partir des données de station :

```bash
python backend/scripts/test_station_detection.py /chemin/vers/fichier.mp3 --station-id 1 --station-name "Radio Sénégal"
```

### Options du script

- `audio_file` (obligatoire) : Chemin vers le fichier audio à tester
- `--station-id` (optionnel, défaut: 1) : ID de la station
- `--station-name` (optionnel, défaut: "Test Station") : Nom de la station

## Intégration dans le code

### Utilisation dans le code Python

```python
from backend.detection.audio_processor.track_manager import TrackManager
from backend.models.database import get_db_session
from datetime import datetime

async def detect_track_from_station(audio_data: bytes, station_id: int, station_name: str):
    # Créer les données de station
    station_data = {
        "raw_audio": audio_data,
        "station_id": station_id,
        "station_name": station_name,
        "timestamp": datetime.now().isoformat()
    }

    # Initialiser le gestionnaire de pistes
    db_session = next(get_db_session())
    track_manager = TrackManager(db_session)

    # Traiter les données de station
    result = await track_manager.process_station_data(station_data)

    return result
```

## Dépannage

### Problèmes courants

1. **Aucun morceau détecté** : Cela peut être dû à plusieurs raisons :
   - Le morceau n'est pas dans la base de données AcoustID
   - La qualité audio est trop faible
   - Le segment audio ne contient pas assez de musique (par exemple, s'il contient principalement de la parole)

2. **Erreur de connexion à AcoustID** : Vérifiez que la clé API AcoustID est correctement configurée et que le service est accessible.

3. **Erreur de génération d'empreinte** : Vérifiez que `fpcalc` est correctement installé et accessible.

### Logs

Les logs de détection sont disponibles dans les fichiers suivants :

- `logs/categories/detection.log` : Logs généraux de détection
- `logs/categories/acoustid.log` : Logs spécifiques à AcoustID
- `logs/categories/track_manager.log` : Logs du gestionnaire de pistes

## Références

- [Documentation AcoustID](../api_integration/acoustid_usage.md)
- [Dépannage AcoustID](../troubleshooting/acoustid_integration.md)
