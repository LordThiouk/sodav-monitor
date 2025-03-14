# Analytics Router Module

Ce module gère toutes les opérations liées aux analyses et statistiques dans le système SODAV Monitor.

## Structure

Le routeur analytics est divisé en cinq composants principaux :

1. **Overview (`overview.py`)** : Aperçu général des statistiques
   - Vue d'ensemble du tableau de bord
   - Tendances et analyses temporelles
   - Statistiques globales du système

2. **Stations (`stations.py`)** : Statistiques des stations radio
   - Statistiques par station
   - Détections par station
   - État et performance des stations

3. **Artists (`artists.py`)** : Statistiques des artistes
   - Statistiques par artiste
   - Temps de jeu par artiste
   - Détections par artiste

4. **Tracks (`tracks.py`)** : Statistiques des pistes
   - Statistiques par piste
   - Temps de jeu par piste
   - Détections par piste

5. **Export (`export.py`)** : Exportation des données
   - Exportation des statistiques dans différents formats
   - Génération de rapports personnalisés

## Endpoints

### Overview Endpoints

- `GET /api/analytics/overview` : Obtenir un aperçu général des statistiques
- `GET /api/analytics/dashboard` : Obtenir les statistiques du tableau de bord
- `GET /api/analytics/trends` : Obtenir les tendances sur une période spécifiée
- `GET /api/analytics/stats` : Obtenir les statistiques pour une période spécifique

### Stations Endpoints

- `GET /api/analytics/stations` : Obtenir les statistiques de toutes les stations
- `GET /api/analytics/stations/stats` : Obtenir les statistiques d'une station spécifique ou de toutes les stations
- `GET /api/analytics/stations/{station_id}/stats` : Obtenir les statistiques détaillées d'une station spécifique

### Artists Endpoints

- `GET /api/analytics/artists` : Obtenir les statistiques de tous les artistes
- `GET /api/analytics/artists/stats` : Obtenir les statistiques d'un artiste spécifique ou de tous les artistes

### Tracks Endpoints

- `GET /api/analytics/tracks` : Obtenir les statistiques de toutes les pistes
- `GET /api/analytics/tracks/{track_id}/stats` : Obtenir les statistiques d'une piste spécifique

### Export Endpoints

- `GET /api/analytics/export` : Exporter les données d'analyse dans un format spécifié (json, csv, xlsx)

## Authentification

Tous les endpoints nécessitent une authentification. L'utilisateur doit être connecté et avoir un token JWT valide.

## Gestion des erreurs

Tous les endpoints incluent une gestion appropriée des erreurs pour les scénarios courants :

- 404 Not Found : Lorsqu'une station, un artiste ou une piste n'existe pas
- 400 Bad Request : Lorsque la validation des entrées échoue
- 401 Unauthorized : Lorsque l'authentification échoue
- 500 Internal Server Error : Lorsque le traitement des statistiques échoue

## Dépendances

Ce module dépend de :

- `backend.models.database` : Accès à la base de données
- `backend.models.models` : Modèles de données
- `backend.utils.auth` : Utilitaires d'authentification
- `backend.analytics.stats_manager` : Gestionnaire de statistiques

## Exemple d'utilisation

```python
# Obtenir un aperçu des statistiques
response = await client.get("/api/analytics/overview", headers=auth_headers)
overview = response.json()

# Obtenir les statistiques d'une station spécifique
response = await client.get(f"/api/analytics/stations/{station_id}/stats", headers=auth_headers)
station_stats = response.json()

# Obtenir les statistiques d'un artiste
response = await client.get("/api/analytics/artists/stats?artist_id=1", headers=auth_headers)
artist_stats = response.json()

# Exporter les données d'analyse au format CSV
response = await client.get("/api/analytics/export?format=csv", headers=auth_headers)
export_data = response.json()
```
