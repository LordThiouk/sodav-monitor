# SODAV Monitor - Système de Monitoring Radio/TV

## Vue d'ensemble

SODAV Monitor est un système automatisé de surveillance des diffusions musicales pour les chaînes de radio et de télévision sénégalaises. Le système utilise des technologies avancées de reconnaissance audio et de traitement du signal pour identifier en temps réel les morceaux de musique diffusés.

## Architecture du Système

### Structure du Projet
```
sodav-monitor/
├── backend/                 # API et logique métier
│   ├── routers/            # Points d'entrée API
│   │   ├── analytics/      # Endpoints statistiques
│   │   ├── channels.py     # Gestion des stations
│   │   └── reports.py      # Génération rapports
│   ├── models.py           # Modèles de données
│   ├── schemas.py          # Schémas Pydantic
│   ├── music_recognition.py # Algorithme reconnaissance
│   └── audio_processor.py  # Traitement audio
│
├── frontend/               # Interface utilisateur
│   ├── src/
│   │   ├── components/     # Composants React
│   │   ├── pages/         # Pages de l'application
│   │   └── services/      # Services API
│   └── public/            # Assets statiques
```

## Algorithme de Reconnaissance

### 1. Capture et Prétraitement Audio
- Échantillonnage du flux audio en segments de 15 secondes
- Conversion en format standard pour analyse
- Normalisation du signal audio

### 2. Détection de Musique (music_recognition.py)
1. **Analyse des Caractéristiques Audio**
   - Calcul du centroïde spectral
   - Mesure de l'énergie RMS
   - Analyse du taux de passage à zéro
   - Évaluation du rolloff spectral
   
2. **Score de Probabilité Musicale**
   ```python
   music_score = (
       (spectral_centroid_weight * 25) +
       (rms_energy_weight * 25) +
       (zero_crossing_rate_weight * 25) +
       (spectral_rolloff_weight * 25)
   )
   ```

### 3. Cascade de Reconnaissance
L'algorithme suit une approche en cascade pour l'identification :

1. **Base de Données Locale**
   - Recherche par empreinte acoustique
   - Cache des empreintes fréquentes
   - Correspondance rapide

2. **MusicBrainz**
   - Identification via API MusicBrainz
   - Récupération métadonnées détaillées
   - Correspondance ISRC

3. **AudD**
   - Service de reconnaissance externe
   - Haute précision pour nouveaux morceaux
   - Enrichissement métadonnées

### 4. Traitement des Résultats
- Calcul durée de lecture
- Agrégation métadonnées
- Enrichissement base de données
- Mise à jour statistiques

## Base de Données

### Schéma Principal
```sql
-- Stations Radio
CREATE TABLE radio_stations (
    id INTEGER PRIMARY KEY,
    name VARCHAR,
    stream_url VARCHAR,
    status VARCHAR,
    is_active BOOLEAN,
    last_checked TIMESTAMP
);

-- Morceaux
CREATE TABLE tracks (
    id INTEGER PRIMARY KEY,
    title VARCHAR,
    artist VARCHAR,
    isrc VARCHAR,
    label VARCHAR,
    play_count INTEGER,
    total_play_time INTERVAL
);

-- Détections
CREATE TABLE track_detections (
    id INTEGER PRIMARY KEY,
    station_id INTEGER,
    track_id INTEGER,
    detected_at TIMESTAMP,
    confidence FLOAT,
    play_duration INTERVAL
);
```

## API Backend

### Points d'Entrée Principaux

1. **Gestion des Stations**
   ```
   GET    /api/channels/              # Liste stations
   POST   /api/channels/refresh       # Rafraîchir stations
   GET    /api/channels/{id}/stats    # Statistiques station
   ```

2. **Détections**
   ```
   POST   /api/detect                 # Détecter morceau
   GET    /api/detections/{id}        # Détails détection
   ```

3. **Statistiques**
   ```
   GET    /api/analytics/overview     # Vue d'ensemble
   GET    /api/analytics/tracks       # Stats morceaux
   GET    /api/analytics/artists      # Stats artistes
   ```

## Interface Utilisateur

### Composants Principaux

1. **Dashboard**
   - Vue d'ensemble temps réel
   - Graphiques statistiques
   - Alertes et notifications

2. **Monitoring Stations**
   - État des connexions
   - Qualité signal
   - Historique détections

3. **Rapports**
   - Génération PDF
   - Export données
   - Filtres personnalisés

### Fonctionnalités Temps Réel
- WebSocket pour détections live
- Mise à jour automatique graphiques
- Notifications événements

## Performances et Optimisations

1. **Cache**
   - Empreintes acoustiques fréquentes
   - Métadonnées morceaux
   - Résultats requêtes communes

2. **Indexation**
   - Index sur ISRC
   - Index temporels détections
   - Index recherche full-text

3. **Parallélisation**
   - Traitement multi-stream
   - Analyses audio parallèles
   - Requêtes API concurrentes

## Sécurité

1. **Authentication**
   - JWT tokens
   - Rôles utilisateurs
   - Sessions sécurisées

2. **Protection Données**
   - Chiffrement connexions
   - Validation entrées
   - Logs sécurisés

## Déploiement

### Prérequis
- Python 3.8+
- Node.js 14+
- PostgreSQL 12+
- FFmpeg

### Configuration
```bash
# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Variables d'Environnement
```env
DATABASE_URL=postgresql://user:pass@localhost/sodav
AUDD_API_KEY=your_key
MUSICBRAINZ_API_KEY=your_key
```

### Lancement
```bash
# Backend
uvicorn main:app --reload

# Frontend
npm run dev
```

## Configuration

1. Créez un fichier `.env` dans le dossier `backend/` :
```env
AUDD_API_KEY=votre_clé_api
DATABASE_URL=sqlite:///./sodav_monitor.db
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

2. Assurez-vous que les URLs des stations radio sont correctement configurées dans `frontend/src/services/radioBrowser.ts`

## Utilisation

1. Lancez le backend : `python main.py`
2. Lancez le frontend : `npm start`
3. Accédez à l'application via `http://localhost:3000`

## Développement

- Backend : Python 3.8+, FastAPI, SQLAlchemy
- Frontend : React 18, TypeScript, Chakra UI
- Base de données : SQLite

## Licence

Copyright © 2025 LordThiouk. Tous droits réservés.
