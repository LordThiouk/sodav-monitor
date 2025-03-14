# Guide d'utilisation de l'API AcoustID

## Introduction

AcoustID est un service d'identification musicale basé sur les empreintes acoustiques. Il permet d'identifier des morceaux de musique à partir d'échantillons audio. Ce document explique comment utiliser correctement l'API AcoustID dans le système SODAV Monitor.

## Prérequis

1. **Clé API AcoustID** : Vous devez disposer d'une clé API valide. Celle-ci doit être configurée dans le fichier `.env.development` avec la variable `ACOUSTID_API_KEY`.

2. **fpcalc** : L'outil `fpcalc` (Chromaprint) doit être installé sur le système. Il est utilisé pour générer les empreintes acoustiques à partir des fichiers audio.

## Configuration

### Configuration de la clé API

La clé API doit être configurée dans le fichier `.env.development` :

```
ACOUSTID_API_KEY=votre_clé_api
```

### Vérification de l'installation de fpcalc

Pour vérifier que `fpcalc` est correctement installé et accessible :

```python
from backend.detection.audio_processor.external_services import get_fpcalc_path

fpcalc_path = get_fpcalc_path()
if fpcalc_path:
    print(f"fpcalc est disponible à : {fpcalc_path}")
else:
    print("fpcalc n'est pas disponible sur le système")
```

## Utilisation de l'API AcoustID

### Initialisation du service

```python
from backend.detection.audio_processor.external_services import AcoustIDService

# Initialisation avec la clé API configurée dans l'environnement
acoustid_service = AcoustIDService()

# Ou initialisation avec une clé API spécifique
acoustid_service = AcoustIDService(api_key="votre_clé_api")
```

### Détection d'un morceau à partir de données audio

```python
import asyncio

async def detect_track(audio_data: bytes):
    # Initialiser le service
    acoustid_service = AcoustIDService()

    # Détecter le morceau
    result = await acoustid_service.detect_track(audio_data)

    if result:
        print(f"Morceau détecté : {result.get('title')} par {result.get('artist')}")
        print(f"Confiance : {result.get('confidence')}")
    else:
        print("Aucun morceau détecté")

# Exemple d'utilisation
with open("chemin/vers/fichier.mp3", "rb") as f:
    audio_data = f.read()

asyncio.run(detect_track(audio_data))
```

### Détection avec retry

Pour une meilleure fiabilité, utilisez la méthode `detect_track_with_retry` qui essaiera plusieurs fois en cas d'échec :

```python
result = await acoustid_service.detect_track_with_retry(audio_data, max_retries=3)
```

### Test de l'API

Pour vérifier que l'API fonctionne correctement :

```python
api_works = await acoustid_service.test_acoustid_api()
if api_works:
    print("L'API AcoustID fonctionne correctement")
else:
    print("Problème avec l'API AcoustID")
```

## Structure des résultats

Lorsqu'un morceau est détecté, le résultat est un dictionnaire contenant les informations suivantes :

```python
{
    "title": "Titre du morceau",
    "artist": "Nom de l'artiste",
    "album": "Nom de l'album",
    "isrc": "Code ISRC (si disponible)",
    "label": "Label (si disponible)",
    "release_date": "Date de sortie (si disponible)",
    "id": "ID AcoustID",
    "confidence": 0.95,  # Score de confiance entre 0 et 1
    "source": "acoustid",
    "detection_method": "acoustid"
}
```

## Bonnes pratiques

1. **Ne pas modifier les empreintes** : Utilisez toujours les empreintes générées par `fpcalc` sans les modifier.

2. **Gérer les erreurs** : Implémentez une gestion des erreurs robuste pour traiter les cas où l'API ne répond pas ou renvoie une erreur.

3. **Utiliser le retry** : Utilisez la méthode `detect_track_with_retry` pour améliorer la fiabilité de la détection.

4. **Vérifier la confiance** : Vérifiez toujours le score de confiance (`confidence`) avant d'utiliser les résultats. Un score faible peut indiquer une détection incorrecte.

5. **Tester régulièrement** : Utilisez la méthode `test_acoustid_api` pour vérifier régulièrement que l'API fonctionne correctement.

## Dépannage

En cas de problème avec l'API AcoustID, consultez le document [Dépannage de l'intégration AcoustID](../troubleshooting/acoustid_integration.md).

## Références

- [Documentation officielle AcoustID](https://acoustid.org/webservice)
- [Documentation Chromaprint (fpcalc)](https://acoustid.org/chromaprint)
