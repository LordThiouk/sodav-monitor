# Suivi du Temps de Lecture dans SODAV Monitor

Ce document explique comment le système SODAV Monitor suit et enregistre le temps exact pendant lequel un son a été joué dans chaque station radio.

## Vue d'ensemble

Le suivi précis du temps de lecture est une fonctionnalité essentielle du système SODAV Monitor. Il permet de :

1. Calculer avec précision les redevances dues aux artistes et aux labels
2. Générer des rapports détaillés sur l'utilisation de la musique
3. Analyser les tendances de diffusion sur différentes périodes

## Architecture du Système

### 1. Modèle de Données

Le temps de lecture est principalement stocké dans la table `track_detections` via le champ `play_duration` :

```python
class TrackDetection(Base):
    __tablename__ = 'track_detections'
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey('radio_stations.id'), index=True)
    track_id = Column(Integer, ForeignKey('tracks.id'), index=True)
    confidence = Column(Float)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, index=True)
    play_duration = Column(Interval)  # Stocké comme un intervalle PostgreSQL
    fingerprint = Column(String)
    audio_hash = Column(String, index=True)
    _is_valid = Column("is_valid", Boolean, default=True)
```

Le champ `play_duration` est de type `Interval`, ce qui permet de stocker précisément la durée sous forme d'intervalle PostgreSQL.

### 2. Flux de Traitement

Le suivi du temps de lecture suit le flux suivant :

1. **Capture Audio** : Le `StreamHandler` capture un segment audio d'une station radio
2. **Extraction des Caractéristiques** : Le `FeatureExtractor` extrait les caractéristiques audio et calcule la durée du segment
3. **Détection de Musique** : Le système détermine si le segment contient de la musique
4. **Détection Hiérarchique** : Si c'est de la musique, le système tente d'identifier la piste via plusieurs méthodes (locale, MusicBrainz, AudD)
5. **Suivi de la Piste** : Si une piste est détectée, le `TrackManager` commence à suivre sa durée de lecture
6. **Accumulation de la Durée** : Si la même piste continue d'être détectée, la durée est accumulée
7. **Enregistrement de la Détection** : Lorsque la piste change ou que la diffusion s'arrête, la détection est enregistrée avec la durée totale

## Composants Clés

### 1. StreamHandler

Le `StreamHandler` est responsable de la capture des données audio à partir des flux radio. Il fournit des méthodes pour :

- Capturer des segments audio
- Gérer le buffer audio
- Traiter les chunks audio entrants

### 2. FeatureExtractor

Le `FeatureExtractor` extrait les caractéristiques audio et calcule la durée du segment. La méthode `get_audio_duration` calcule la durée en secondes en divisant le nombre d'échantillons par la fréquence d'échantillonnage :

```python
def get_audio_duration(self, audio_data: np.ndarray) -> float:
    """Calcule la durée de l'audio en secondes."""
    # Obtenir le nombre d'échantillons (gérer mono et stéréo)
    if len(audio_data.shape) == 1:
        # Mono
        n_samples = audio_data.shape[0]
    elif len(audio_data.shape) == 2:
        # Stéréo ou mono avec dimension explicite
        n_samples = audio_data.shape[0]
    else:
        raise ValueError(f"Unexpected audio data shape: {audio_data.shape}")
        
    # Calculer la durée en secondes
    duration = float(n_samples / self.sample_rate)
    
    return duration
```

### 3. Services de Détection Externes

Le système utilise plusieurs services pour identifier les pistes musicales :

#### a. MusicBrainzService

Ce service utilise l'API MusicBrainz pour identifier les pistes musicales :

```python
class MusicBrainzService:
    """Service pour interagir avec l'API MusicBrainz."""
    
    async def detect_track(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Détecte une piste en utilisant l'API MusicBrainz."""
        # Appel à l'API MusicBrainz
        # ...
        return {
            "title": result["title"],
            "artist": result["artist"],
            "confidence": result["score"]
        }
```

#### b. AuddService

Ce service utilise l'API AudD pour identifier les pistes musicales :

```python
class AuddService:
    """Service pour interagir avec l'API AudD."""
    
    async def detect_track(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Détecte une piste en utilisant l'API AudD."""
        # Appel à l'API AudD
        # ...
        return {
            "title": track["title"],
            "artist": track["artist"],
            "confidence": track["score"]
        }
```

#### c. MusicBrainzRecognizer

Ce composant coordonne le processus de reconnaissance en utilisant plusieurs services :

```python
class MusicBrainzRecognizer:
    async def recognize_from_audio_data(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Analyse l'audio et tente la reconnaissance en utilisant plusieurs services dans l'ordre:
        1. Détection locale
        2. MusicBrainz/AcoustID
        3. Audd
        """
        # Analyse des caractéristiques audio
        # Détection locale
        # Détection MusicBrainz/AcoustID
        # Détection AudD
        # ...
```

### 4. TrackManager

Le `TrackManager` est responsable du suivi des pistes en cours de lecture. Il maintient un dictionnaire `current_tracks` qui suit les pistes pour chaque station.

#### Détection Hiérarchique

Le `TrackManager` implémente une détection hiérarchique pour identifier les pistes :

```python
async def find_local_match(self, features: np.ndarray) -> Optional[Dict[str, Any]]:
    """Recherche une correspondance dans la base de données locale."""
    # Extraction d'empreinte digitale et recherche locale
    # ...

async def find_musicbrainz_match(self, features: np.ndarray) -> Optional[Dict[str, Any]]:
    """Recherche une correspondance via l'API MusicBrainz."""
    # Conversion des caractéristiques en audio
    # Appel au service MusicBrainz
    # Création/récupération de l'artiste et de la piste
    # ...

async def find_audd_match(self, features: np.ndarray) -> Optional[Dict[str, Any]]:
    """Recherche une correspondance via l'API AudD."""
    # Conversion des caractéristiques en audio
    # Appel au service AudD
    # Création/récupération de l'artiste et de la piste
    # ...
```

#### Démarrage du Suivi

Lorsqu'une nouvelle piste est détectée, le suivi commence avec la méthode `_start_track_detection` :

```python
def _start_track_detection(self, track: Track, station_id: int, features: Dict[str, Any]) -> Dict[str, Any]:
    """Démarre le suivi d'une nouvelle piste."""
    start_time = datetime.utcnow()
    self.current_tracks[station_id] = {
        "track": track,
        "start_time": start_time,
        "play_duration": timedelta(seconds=features.get("play_duration", 0)),
        "features": features
    }
    
    return {
        "track_id": track.id,
        "start_time": start_time.isoformat(),
        "confidence": features.get("confidence", 0)
    }
```

#### Mise à Jour de la Durée

Si la même piste continue d'être détectée, la durée est mise à jour avec la méthode `_update_current_track` :

```python
def _update_current_track(self, station_id: int, features: Dict[str, Any]) -> Dict[str, Any]:
    """Met à jour les informations de la piste en cours."""
    current = self.current_tracks[station_id]
    current["play_duration"] += timedelta(seconds=features.get("play_duration", 0))
    current["features"] = features
    
    return {
        "status": "playing",
        "track": current["track"].to_dict(),
        "play_duration": current["play_duration"].total_seconds()
    }
```

#### Fin du Suivi

Lorsque la piste change ou que la diffusion s'arrête, la détection est enregistrée avec la méthode `_end_current_track` :

```python
def _end_current_track(self, station_id: int):
    """Termine le suivi de la piste en cours."""
    if station_id in self.current_tracks:
        current = self.current_tracks[station_id]
        
        # Enregistre la détection
        detection = TrackDetection(
            track_id=current["track"].id,
            station_id=station_id,
            detected_at=current["start_time"],
            end_time=datetime.utcnow(),
            play_duration=current["play_duration"],
            fingerprint=current["features"].get("fingerprint", ""),
            audio_hash=current["features"].get("audio_hash", ""),
            confidence=current["features"].get("confidence", 0)
        )
        self.db_session.add(detection)
        
        # Met à jour les statistiques
        self._update_station_track_stats(
            station_id,
            current["track"].id,
            current["play_duration"]
        )
        
        # Supprime la piste courante
        del self.current_tracks[station_id]
        
        # Commit les changements
        self.db_session.commit()
```

### 5. AudioProcessor

L'`AudioProcessor` coordonne le processus de détection et s'assure que la durée de lecture est correctement incluse dans les résultats de détection :

```python
async def process_stream(self, audio_data: np.ndarray, station_id: Optional[int] = None) -> Dict[str, Any]:
    """Traite un segment audio pour détecter la présence de musique."""
    # Extraire les caractéristiques audio
    features = self.feature_extractor.extract_features(audio_data)
    
    # Récupérer la durée de lecture
    play_duration = features.get("play_duration", 0.0)
    
    # Vérifier si c'est de la musique
    is_music = features.get("is_music", False)
    
    if not is_music:
        return {
            "type": "speech",
            "confidence": 0.0,
            "station_id": station_id,
            "play_duration": play_duration
        }
    
    # Détection hiérarchique (locale, MusicBrainz, AudD)
    # ...
    
    # Inclure la durée de lecture dans le résultat
    return {
        "type": "music",
        "source": "local",
        "confidence": match["confidence"],
        "track": match["track"],
        "station_id": station_id,
        "play_duration": play_duration
    }
```

## Statistiques et Rapports

Le système utilise les durées de lecture enregistrées pour générer des statistiques et des rapports :

### 1. Statistiques par Artiste

```sql
SELECT 
    a.name AS artist_name,
    SUM(td.play_duration) AS total_play_time,
    COUNT(td.id) AS total_plays
FROM 
    artists a
JOIN 
    tracks t ON a.id = t.artist_id
JOIN 
    track_detections td ON t.id = td.track_id
GROUP BY 
    a.id, a.name
ORDER BY 
    total_play_time DESC;
```

### 2. Statistiques par Station

```sql
SELECT 
    rs.name AS station_name,
    SUM(td.play_duration) AS total_play_time,
    COUNT(td.id) AS total_detections
FROM 
    radio_stations rs
JOIN 
    track_detections td ON rs.id = td.station_id
GROUP BY 
    rs.id, rs.name
ORDER BY 
    total_play_time DESC;
```

### 3. Statistiques par Piste et Station

```sql
SELECT 
    rs.name AS station_name,
    t.title AS track_title,
    a.name AS artist_name,
    SUM(td.play_duration) AS total_play_time,
    COUNT(td.id) AS play_count
FROM 
    track_detections td
JOIN 
    tracks t ON td.track_id = t.id
JOIN 
    artists a ON t.artist_id = a.id
JOIN 
    radio_stations rs ON td.station_id = rs.id
GROUP BY 
    rs.id, rs.name, t.id, t.title, a.id, a.name
ORDER BY 
    rs.name, total_play_time DESC;
```

### 4. Statistiques par Source de Détection

```sql
SELECT 
    t.source AS detection_source,
    COUNT(td.id) AS detection_count,
    SUM(td.play_duration) AS total_play_time
FROM 
    track_detections td
JOIN 
    tracks t ON td.track_id = t.id
GROUP BY 
    t.source
ORDER BY 
    total_play_time DESC;
```

## Validation et Contrôle

Le système inclut plusieurs mécanismes pour s'assurer que les durées de lecture sont valides :

### 1. Vérifications de Base de Données

```python
# Vérifier les durées invalides
invalid_durations = db.query(TrackDetection).filter(
    (TrackDetection.play_duration <= 0) |
    (TrackDetection.play_duration > 3600)  # Max 1 heure
).all()
```

### 2. Détection des Valeurs Manquantes

```python
# Vérifier les détections sans durée
missing_durations = db.query(TrackDetection).filter(
    (TrackDetection.play_duration == timedelta(0)) |
    (TrackDetection.play_duration == None)
).all()
```

### 3. Validation des Sources de Détection

```python
# Vérifier les détections par source
detection_sources = db.query(
    Track.source, 
    func.count(TrackDetection.id).label('count')
).join(
    TrackDetection, TrackDetection.track_id == Track.id
).group_by(
    Track.source
).all()
```

## Conclusion

Le système SODAV Monitor implémente un suivi précis du temps de lecture pour chaque détection de musique. La durée est calculée à partir des données audio, accumulée pendant la diffusion continue d'une piste, et enregistrée dans la base de données lorsque la détection se termine.

Le système utilise une approche hiérarchique pour la détection des pistes musicales, en commençant par une recherche locale, puis en utilisant des services externes comme MusicBrainz et AudD si nécessaire. Cette approche permet d'optimiser la précision de la détection tout en minimisant les coûts liés aux API externes.

Cette architecture permet de générer des statistiques précises et des rapports détaillés sur l'utilisation de la musique, ce qui est essentiel pour le calcul des redevances et l'analyse des tendances de diffusion. 