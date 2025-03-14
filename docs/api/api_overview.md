# Documentation API SODAV Monitor

## Introduction

L'API SODAV Monitor permet de surveiller les stations de radio, détecter les morceaux de musique diffusés, et générer des rapports d'analyse. Cette documentation détaille les endpoints disponibles, leurs paramètres, et les formats de réponse.

## Base URL

```
https://sodav-monitor-production.up.railway.app/api
```

Pour le développement local :

```
http://localhost:8000/api
```

## Authentification

L'API utilise l'authentification JWT (JSON Web Token). Pour accéder aux endpoints protégés, vous devez inclure un token d'accès dans l'en-tête `Authorization` de vos requêtes.

### Obtenir un token d'authentification

**Endpoint**: `POST /auth/login`

**Corps de la requête**:
```json
{
  "username": "votre_email@exemple.com",
  "password": "votre_mot_de_passe"
}
```

**Réponse**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Utilisation du token**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Stations Radio

### Obtenir toutes les stations

**Endpoint**: `GET /channels/`

**Paramètres de requête**:
- `country` (optionnel): Filtrer par code pays
- `language` (optionnel): Filtrer par code langue
- `status` (optionnel): Filtrer par statut de la station
- `is_active` (optionnel): Filtrer par statut actif
- `skip` (optionnel, défaut: 0): Nombre d'enregistrements à sauter
- `limit` (optionnel, défaut: 100): Nombre maximum d'enregistrements à retourner

**Réponse**:
```json
[
  {
    "id": 1,
    "name": "Radio Sénégal",
    "stream_url": "http://stream.example.com/radio",
    "country": "SN",
    "language": "fr",
    "is_active": true,
    "last_checked": "2024-03-01T12:00:00",
    "status": "active"
  }
]
```

### Créer une station

**Endpoint**: `POST /channels/`

**Corps de la requête**:
```json
{
  "name": "Nouvelle Radio",
  "stream_url": "http://stream.example.com/nouvelle-radio",
  "country": "SN",
  "language": "fr"
}
```

**Réponse**:
```json
{
  "id": 2,
  "name": "Nouvelle Radio",
  "stream_url": "http://stream.example.com/nouvelle-radio",
  "country": "SN",
  "language": "fr",
  "is_active": true,
  "last_checked": "2024-03-01T12:00:00",
  "status": "pending"
}
```

### Obtenir une station spécifique

**Endpoint**: `GET /channels/{station_id}`

**Réponse**:
```json
{
  "id": 1,
  "name": "Radio Sénégal",
  "stream_url": "http://stream.example.com/radio",
  "country": "SN",
  "language": "fr",
  "is_active": true,
  "last_checked": "2024-03-01T12:00:00",
  "status": "active"
}
```

### Mettre à jour une station

**Endpoint**: `PUT /channels/{station_id}`

**Corps de la requête**:
```json
{
  "name": "Radio Sénégal Modifiée",
  "is_active": false
}
```

**Réponse**:
```json
{
  "id": 1,
  "name": "Radio Sénégal Modifiée",
  "stream_url": "http://stream.example.com/radio",
  "country": "SN",
  "language": "fr",
  "is_active": false,
  "last_checked": "2024-03-01T12:00:00",
  "status": "active"
}
```

### Supprimer une station

**Endpoint**: `DELETE /channels/{station_id}`

**Réponse**:
```json
{
  "message": "Station supprimée avec succès"
}
```

### Obtenir les statistiques d'une station

**Endpoint**: `GET /channels/{station_id}/stats`

**Réponse**:
```json
{
  "total_detections": 1250,
  "unique_tracks": 320,
  "unique_artists": 180,
  "average_confidence": 0.92,
  "total_play_time": "42:15:30",
  "detection_rate": 52.1,
  "top_tracks": [
    {
      "title": "Titre de la chanson",
      "artist": "Nom de l'artiste",
      "plays": 25,
      "play_time": "01:15:45"
    }
  ],
  "top_artists": [
    {
      "name": "Nom de l'artiste",
      "plays": 42,
      "play_time": "02:30:15"
    }
  ]
}
```

### Obtenir les détections d'une station

**Endpoint**: `GET /channels/{station_id}/detections`

**Paramètres de requête**:
- `page` (optionnel, défaut: 1): Numéro de page
- `limit` (optionnel, défaut: 10): Nombre d'éléments par page
- `search` (optionnel): Recherche par titre ou artiste
- `label` (optionnel): Filtrer par label

**Réponse**:
```json
{
  "detections": [
    {
      "id": 1,
      "station_id": 1,
      "track_id": 1,
      "confidence": 0.95,
      "detected_at": "2024-03-01T12:00:00",
      "play_duration": "00:03:45",
      "track": {
        "title": "Titre de la chanson",
        "artist": "Nom de l'artiste",
        "isrc": "ABCDE1234567",
        "label": "Label de l'artiste",
        "fingerprint": "empreinte_audio_hash"
      }
    }
  ],
  "total": 1250,
  "page": 1,
  "pages": 125,
  "has_next": true,
  "has_prev": false,
  "labels": ["Label 1", "Label 2"],
  "station": {
    "id": 1,
    "name": "Radio Sénégal",
    "country": "SN",
    "language": "fr",
    "status": "active",
    "total_detections": 1250,
    "average_confidence": 0.92,
    "total_play_duration": "42:15:30"
  }
}
```

### Lancer la détection sur une station spécifique

**Endpoint**: `POST /channels/{channel_id}/detect-music`

**Description**: Déclenche le processus de détection de musique sur une station radio spécifique.

**Authentification**: Requiert un token JWT valide.

**Réponse**:
```json
{
  "status": "success",
  "message": "Successfully processed station [Nom de la station]",
  "details": {
    "station_id": 1,
    "station_name": "Radio Sénégal",
    "detections": [
      {
        "detection": {
          "title": "Titre de la chanson",
          "artist": "Nom de l'artiste",
          "confidence": 0.95
        }
      }
    ]
  }
}
```

### Lancer la détection sur toutes les stations actives

**Endpoint**: `POST /detect-music-all`

**Description**: Déclenche le processus de détection de musique sur toutes les stations radio actives.

**Paramètres de requête**:
- `max_stations` (optionnel, défaut: 5): Nombre maximum de stations à traiter simultanément.

**Authentification**: Requiert un token JWT valide.

**Réponse**:
```json
{
  "status": "success",
  "message": "Detection started for X active stations",
  "details": {
    "total_stations": 10,
    "processed_stations": 5,
    "status": "in_progress"
  }
}
```

### Rafraîchir une station

**Endpoint**: `POST /channels/{channel_id}/refresh`

**Description**: Rafraîchit les informations d'une station spécifique, vérifie son état et met à jour son statut.

**Authentification**: Requiert un token JWT valide.

**Réponse**:
```json
{
  "status": "success",
  "message": "Channel 1 refreshed successfully",
  "details": {
    "is_available": true,
    "content_type": "audio/mpeg",
    "latency": 120
  }
}
```

> **Note importante**: Le frontend fait référence à un endpoint `POST /detect/{stationId}` dans le fichier `frontend/src/services/api.ts` via la fonction `detectAudio()`, mais cet endpoint ne semble pas être implémenté dans le backend. Il est possible que cet endpoint ait été remplacé par `POST /channels/{channel_id}/detect-music` qui offre une fonctionnalité similaire. Assurez-vous de mettre à jour le frontend pour utiliser l'endpoint correct ou d'implémenter l'endpoint manquant dans le backend.

## Détections

### Obtenir toutes les détections

**Endpoint**: `GET /detections/`

**Paramètres de requête**:
- `skip` (optionnel, défaut: 0): Nombre d'enregistrements à sauter
- `limit` (optionnel, défaut: 100): Nombre maximum d'enregistrements à retourner
- `station_id` (optionnel): Filtrer par ID de station
- `start_date` (optionnel): Filtrer par date de début (format ISO)
- `end_date` (optionnel): Filtrer par date de fin (format ISO)
- `confidence_threshold` (optionnel): Seuil minimum de confiance (0.0 à 1.0)

**Réponse**:
```json
[
  {
    "id": 1,
    "track": {
      "id": 1,
      "title": "Titre de la chanson",
      "artist": "Nom de l'artiste",
      "isrc": "ABCDE1234567",
      "label": "Label de l'artiste",
      "fingerprint": "empreinte_audio_hash",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    },
    "station": {
      "id": 1,
      "name": "Radio Sénégal",
      "stream_url": "http://stream.example.com/radio",
      "country": "SN",
      "language": "fr",
      "is_active": true,
      "last_checked": "2024-03-01T12:00:00",
      "status": "active"
    },
    "detected_at": "2024-03-01T12:00:00",
    "confidence": 0.95,
    "play_duration": 225
  }
]
```

## Analytiques

### Obtenir un aperçu des analytiques

**Endpoint**: `GET /analytics/overview`

**Paramètres de requête**:
- `time_range` (optionnel, défaut: "24h"): Plage de temps ("24h", "7d", "30d", "all")

**Réponse**:
```json
{
  "totalDetections": 5280,
  "detectionRate": 220,
  "activeStations": 42,
  "totalStations": 50,
  "averageConfidence": 0.89,
  "detectionsByHour": [
    { "hour": 0, "count": 180 },
    { "hour": 1, "count": 165 }
  ],
  "topArtists": [
    { "name": "Artiste 1", "count": 120 },
    { "name": "Artiste 2", "count": 95 }
  ],
  "systemHealth": {
    "status": "healthy",
    "uptime": 345600,
    "lastError": null
  }
}
```

### Obtenir des statistiques par période

**Endpoint**: `GET /analytics/stats`

**Paramètres de requête**:
- `start_date` (obligatoire): Date de début (format ISO)
- `end_date` (obligatoire): Date de fin (format ISO)

**Réponse**:
```json
{
  "total_detections": 5280,
  "unique_tracks": 1250,
  "unique_artists": 750,
  "total_play_time": "220:15:30",
  "average_confidence": 0.89
}
```

## Rapports

### Obtenir tous les rapports

**Endpoint**: `GET /reports/`

**Paramètres de requête**:
- `skip` (optionnel, défaut: 0): Nombre d'enregistrements à sauter
- `limit` (optionnel, défaut: 100): Nombre maximum d'enregistrements à retourner
- `report_type` (optionnel): Type de rapport
- `start_date` (optionnel): Filtrer par date de début (format ISO)
- `end_date` (optionnel): Filtrer par date de fin (format ISO)

**Réponse**:
```json
[
  {
    "id": 1,
    "title": "Rapport quotidien - 2024-03-01",
    "type": "daily",
    "format": "pdf",
    "period_start": "2024-03-01T00:00:00",
    "period_end": "2024-03-01T23:59:59",
    "filters": null,
    "status": "completed",
    "file_path": "/reports/rapport_quotidien_20240301.pdf",
    "error_message": null,
    "created_at": "2024-03-02T00:01:00",
    "updated_at": "2024-03-02T00:05:00"
  }
]
```

### Créer un rapport

**Endpoint**: `POST /reports/`

**Corps de la requête**:
```json
{
  "title": "Rapport personnalisé",
  "type": "comprehensive",
  "format": "pdf",
  "period_start": "2024-02-01T00:00:00",
  "period_end": "2024-02-29T23:59:59",
  "filters": {
    "artists": ["Artiste 1", "Artiste 2"],
    "stations": [1, 2, 3]
  }
}
```

**Réponse**:
```json
{
  "id": 2,
  "title": "Rapport personnalisé",
  "type": "comprehensive",
  "format": "pdf",
  "period_start": "2024-02-01T00:00:00",
  "period_end": "2024-02-29T23:59:59",
  "filters": {
    "artists": ["Artiste 1", "Artiste 2"],
    "stations": [1, 2, 3]
  },
  "status": "pending",
  "file_path": null,
  "error_message": null,
  "created_at": "2024-03-02T10:00:00",
  "updated_at": "2024-03-02T10:00:00"
}
```

### Générer un rapport

**Endpoint**: `POST /reports/generate`

**Corps de la requête**:
```json
{
  "report_type": "daily",
  "format": "pdf",
  "start_date": "2024-03-01T00:00:00",
  "end_date": "2024-03-01T23:59:59",
  "include_graphs": true,
  "language": "fr"
}
```

**Réponse**:
```json
{
  "status": "success",
  "report_id": 3,
  "message": "Rapport en cours de génération"
}
```

### Télécharger un rapport

**Endpoint**: `GET /reports/{report_id}/download`

**Réponse**: Fichier de rapport (PDF, CSV, XLSX, etc.)

### Envoyer un rapport par email

**Endpoint**: `POST /reports/{report_id}/send`

**Corps de la requête**:
```json
{
  "email": "destinataire@exemple.com",
  "subject": "Rapport SODAV Monitor",
  "body": "Veuillez trouver ci-joint le rapport demandé."
}
```

**Réponse**:
```json
{
  "status": "success",
  "message": "Rapport envoyé avec succès"
}
```

## WebSockets

L'API SODAV Monitor propose également des connexions WebSocket pour recevoir des mises à jour en temps réel.

### URL de connexion WebSocket

```
wss://sodav-monitor-production.up.railway.app/api/ws
```

Pour le développement local :

```
ws://localhost:8000/api/ws
```

### Types de messages

#### Mise à jour de détection

```json
{
  "type": "detection",
  "data": {
    "id": 1,
    "station_id": 1,
    "station_name": "Radio Sénégal",
    "track": {
      "title": "Titre de la chanson",
      "artist": "Nom de l'artiste",
      "isrc": "ABCDE1234567",
      "label": "Label de l'artiste"
    },
    "detected_at": "2024-03-01T12:00:00",
    "confidence": 0.95,
    "play_duration": 225
  }
}
```

#### Mise à jour des statistiques

```json
{
  "type": "stats_update",
  "data": {
    "total_detections": 5280,
    "active_stations": 42,
    "detection_rate": 220,
    "last_update": "2024-03-01T12:05:00"
  }
}
```

## Codes d'erreur

| Code | Description |
|------|-------------|
| 400 | Requête invalide |
| 401 | Non authentifié |
| 403 | Non autorisé |
| 404 | Ressource non trouvée |
| 422 | Erreur de validation |
| 429 | Trop de requêtes |
| 500 | Erreur interne du serveur |

## Limites de débit

L'API SODAV Monitor implémente des limites de débit pour éviter les abus. Par défaut, la limite est de 100 requêtes par minute par adresse IP ou clé API.

En cas de dépassement de la limite, l'API retournera un code d'erreur 429 avec un en-tête `Retry-After` indiquant le nombre de secondes à attendre avant de réessayer.
