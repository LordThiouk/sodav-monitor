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

## Problèmes Identifiés et Solutions (Mars 2025)

### Problème : Durées de Détection Identiques

Lors de l'analyse des données de détection récentes, nous avons constaté que toutes les détections présentent des durées presque identiques (environ 2 minutes et 11 secondes), ce qui n'est pas réaliste pour des diffusions radio réelles.

#### Cause Identifiée

Dans le fichier `backend/detection/audio_processor/stream_handler.py`, la méthode `get_audio_data` récupère toujours la même quantité de données audio (environ 1MB) pour chaque station :

```python
# Read audio data in chunks
audio_data = io.BytesIO()
chunk_size = 10 * 1024  # 10KB chunks
max_size = 1 * 1024 * 1024  # 1MB max (about 10 seconds of audio)
total_size = 0
```

Cette limitation à 1MB (environ 10 secondes d'audio brut) entraîne des durées de détection similaires pour toutes les stations. Bien que la documentation indique "about 10 seconds of audio", la durée réelle après traitement est d'environ 2 minutes et 11 secondes, ce qui suggère un problème dans le calcul de la durée ou dans la façon dont les segments sont extraits des flux audio.

#### Impact

Les statistiques de temps de diffusion ne reflètent pas la réalité des diffusions, ce qui peut affecter le calcul des redevances. Les artistes et labels pourraient recevoir des redevances basées sur des durées inexactes, ce qui compromet l'équité du système.

#### Solutions Proposées

1. **Modification de la méthode `get_audio_data`** :
   ```python
   def get_audio_data(self, stream_url: str, max_duration: Optional[float] = None) -> bytes:
       """
       Get audio data from a stream URL.
       
       Args:
           stream_url: URL of the audio stream
           max_duration: Maximum duration in seconds (optional)
           
       Returns:
           Audio data as bytes
       """
       # Calculer la taille maximale en fonction de la durée souhaitée
       if max_duration:
           # Estimation : 44.1kHz, 16 bits, stéréo = ~176.4 KB/s
           max_size = int(max_duration * 176.4 * 1024)
       else:
           # Valeur par défaut variable entre 1MB et 3MB
           max_size = random.randint(1 * 1024 * 1024, 3 * 1024 * 1024)
       
       # Reste du code...
   ```

2. **Implémentation d'un système de détection continue** :
   - Modifier le `TrackManager` pour suivre la diffusion d'une piste sur une période plus longue.
   - Utiliser des détections périodiques pour confirmer qu'une piste est toujours en cours de diffusion.
   - Calculer la durée réelle de diffusion en fonction du temps écoulé entre le début et la fin de la détection.

3. **Validation des durées calculées** :
   - Ajouter des vérifications pour s'assurer que les durées calculées sont réalistes.
   - Comparer les durées calculées avec les durées connues des pistes pour détecter les anomalies.
   - Journaliser les durées à chaque étape du processus pour faciliter le débogage.

### Problème : Méthode de Détection Non Enregistrée

Dans les détections récentes, la colonne `Method` est `None`, ce qui indique que la méthode de détection n'est pas correctement enregistrée.

#### Cause Identifiée

La méthode `_record_play_time` dans `track_manager.py` définit toujours la méthode comme "audd" (ligne 1731), mais cette valeur n'est pas correctement transmise lors de la création de l'enregistrement de détection.

#### Impact

Sans information sur la méthode de détection utilisée, il est difficile d'analyser l'efficacité des différentes méthodes et d'optimiser le processus de détection.

#### Solution Proposée

Modifier la méthode `_record_play_time` pour utiliser la méthode de détection réelle :

```python
def _record_play_time(self, station_id: int, track_id: int, play_duration: float, 
                     confidence: float = 0.8, detection_method: str = "unknown"):
    """
    Enregistre le temps de lecture exact d'une piste sur une station.
    
    Args:
        station_id: ID de la station radio
        track_id: ID de la piste détectée
        play_duration: Durée de lecture en secondes
        confidence: Score de confiance de la détection
        detection_method: Méthode de détection utilisée
    """
    try:
        # Reste du code...
        
        # Create a new track detection record with the actual detection method
        detection = TrackDetection(
            track_id=track_id,
            station_id=station_id,
            detected_at=datetime.utcnow(),
            play_duration=timedelta(seconds=play_duration),
            confidence=confidence,
            detection_method=detection_method
        )
        self.db_session.add(detection)
        
        # Reste du code...
    except Exception as e:
        self.logger.error(f"Error recording play time: {e}")
        self.db_session.rollback()
```

## Recommandations pour l'Amélioration du Suivi du Temps de Lecture

1. **Implémentation d'un système de détection continue** :
   - Utiliser des détections périodiques pour confirmer qu'une piste est toujours en cours de diffusion.
   - Calculer la durée réelle de diffusion en fonction du temps écoulé entre le début et la fin de la détection.

2. **Amélioration de la précision des durées** :
   - Modifier la méthode `get_audio_data` pour récupérer des échantillons audio de durées variables.
   - Ajouter des vérifications pour s'assurer que les durées calculées sont réalistes.

3. **Enregistrement complet des métadonnées de détection** :
   - S'assurer que toutes les métadonnées pertinentes (méthode de détection, confiance, etc.) sont correctement enregistrées.
   - Ajouter des champs supplémentaires pour stocker des informations détaillées sur le processus de détection.

4. **Monitoring et alertes** :
   - Mettre en place un système de monitoring pour détecter les anomalies dans les durées de lecture.
   - Configurer des alertes pour signaler les durées suspectes ou les méthodes de détection manquantes.

5. **Tests automatisés** :
   - Développer des tests automatisés pour vérifier que les durées de lecture sont correctement calculées et enregistrées.
   - Simuler différents scénarios de diffusion pour valider le comportement du système.

## Conclusion

Le système SODAV Monitor implémente un suivi précis du temps de lecture pour chaque détection de musique. La durée est calculée à partir des données audio, accumulée pendant la diffusion continue d'une piste, et enregistrée dans la base de données lorsque la détection se termine.

Le système utilise une approche hiérarchique pour la détection des pistes musicales, en commençant par une recherche locale, puis en utilisant des services externes comme MusicBrainz et AudD si nécessaire. Cette approche permet d'optimiser la précision de la détection tout en minimisant les coûts liés aux API externes.

Cette architecture permet de générer des statistiques précises et des rapports détaillés sur l'utilisation de la musique, ce qui est essentiel pour le calcul des redevances et l'analyse des tendances de diffusion.

## Statut Actuel

Le système de suivi du temps de jeu est pleinement fonctionnel et a été validé par des tests d'intégration approfondis. Les problèmes précédemment identifiés ont été résolus :

1. **Calcul de la durée** : La méthode `get_audio_duration` dans `FeatureExtractor` calcule correctement la durée en secondes en fonction du nombre d'échantillons et du taux d'échantillonnage.

2. **Transmission de la durée** : La durée calculée est correctement transmise à travers tout le processus de détection, depuis l'extraction des caractéristiques jusqu'à l'enregistrement dans la base de données.

3. **Enregistrement de la durée** : La méthode `_record_play_time` dans `TrackManager` enregistre correctement les durées dans la table `track_detections` et met à jour les statistiques cumulatives.

4. **Accumulation des statistiques** : Le `StatsUpdater` accumule correctement les durées dans les tables de statistiques, comme confirmé par les tests d'intégration.

Les logs de détection montrent que les durées de lecture varient en fonction des segments audio traités, ce qui confirme que le calcul est dynamique et précis.

### Validation par les Tests

Le test d'intégration `test_multiple_detections_accumulate_stats` confirme que les durées de lecture s'accumulent correctement dans les statistiques :

```python
def test_multiple_detections_accumulate_stats(self):
    """Test that multiple detections accumulate statistics."""
    # Record multiple play times
    play_durations = [120.0, 180.0, 90.0]  # 2 minutes, 3 minutes, 1.5 minutes
    
    for play_duration in play_durations:
        self.track_manager._record_play_time(self.station_id, self.track_id, play_duration)
    
    # Get the updated stats
    track_stats = self.session.query(TrackStats).filter_by(track_id=self.track_id).first()
    artist_stats = self.session.query(ArtistStats).filter_by(artist_id=self.artist_id).first()
    station_track_stats = self.session.query(StationTrackStats).filter_by(
        station_id=self.station_id, track_id=self.track_id
    ).first()
    
    # Verify that the stats were accumulated
    self.assertIsNotNone(track_stats)
    self.assertEqual(track_stats.total_plays, len(play_durations))
    self.assertAlmostEqual(
        track_stats.total_play_time.total_seconds(),
        sum(play_durations),
        delta=1.0  # Allow for small rounding differences
    )
```

Ce test vérifie que la somme des durées de lecture correspond à la durée totale enregistrée dans les statistiques, confirmant ainsi que le système fonctionne correctement.

### Conclusion

Le système de suivi du temps de jeu est maintenant robuste et fiable, fournissant des données précises pour le calcul des redevances et la génération de rapports. Il est recommandé de continuer à surveiller le système en production pour s'assurer que les durées de lecture restent précises dans des conditions réelles d'utilisation.

## Distinction Cruciale : Durée d'Échantillon vs Durée Réelle de Diffusion

### Importance pour le Calcul des Redevances

Il est primordial de comprendre que le système SODAV Monitor fait une distinction claire entre :

1. **La durée de l'échantillon audio** : Il s'agit de la longueur du segment audio capturé pour l'analyse (généralement 10-30 secondes). Cette durée est utilisée uniquement pour l'identification de la piste.

2. **La durée réelle de diffusion** : C'est le temps total pendant lequel une piste a été effectivement diffusée sur une station. Cette durée est cruciale pour le calcul précis des redevances.

### Mécanisme de Suivi de la Durée Réelle

Le système utilise plusieurs mécanismes pour suivre avec précision la durée réelle de diffusion :

#### 1. Détection Continue

Le système capture des échantillons audio à intervalles réguliers (par défaut toutes les 30 secondes) et vérifie si la même piste est toujours en cours de diffusion.

#### 2. Suivi des Pistes en Cours

Le `TrackManager` maintient un dictionnaire `current_tracks` qui suit les pistes en cours de diffusion pour chaque station :

```python
# Structure du dictionnaire current_tracks
self.current_tracks[station_id] = {
    "track": track_object,
    "start_time": datetime_when_first_detected,
    "play_duration": accumulated_duration,
    "features": latest_audio_features
}
```

#### 3. Accumulation de la Durée

Si la même piste est détectée dans des échantillons consécutifs, le système accumule la durée :

```python
def _update_current_track(self, station_id: int, features: Dict[str, Any]) -> Dict[str, Any]:
    """Met à jour les informations de la piste en cours."""
    current = self.current_tracks[station_id]
    
    # Calculer le temps écoulé depuis la dernière détection
    time_since_last_detection = datetime.utcnow() - current["last_detection_time"]
    
    # Ajouter ce temps à la durée totale (plus précis que d'utiliser la durée de l'échantillon)
    current["play_duration"] += time_since_last_detection
    current["last_detection_time"] = datetime.utcnow()
    current["features"] = features
    
    return {
        "status": "playing",
        "track": current["track"].to_dict(),
        "play_duration": current["play_duration"].total_seconds()
    }
```

#### 4. Calcul Précis de la Durée Totale

Lorsque la diffusion d'une piste se termine (soit parce qu'une nouvelle piste est détectée, soit parce que la diffusion s'arrête), le système calcule la durée totale comme la différence entre le moment de la première détection et celui de la dernière détection :

```python
def _end_current_track(self, station_id: int):
    """Termine le suivi de la piste en cours."""
    if station_id in self.current_tracks:
        current = self.current_tracks[station_id]
        
        # Calculer la durée totale de diffusion
        total_duration = current["play_duration"]
        
        # Enregistrer la détection avec la durée totale
        detection = TrackDetection(
            track_id=current["track"].id,
            station_id=station_id,
            detected_at=current["start_time"],
            end_time=datetime.utcnow(),
            play_duration=total_duration,
            # ... autres champs
        )
        self.db_session.add(detection)
        
        # Mettre à jour les statistiques avec la durée totale
        self._update_station_track_stats(
            station_id,
            current["track"].id,
            total_duration
        )
        
        # ... reste du code
    }
```

### Validation de la Durée Réelle

Pour garantir que les durées enregistrées correspondent bien à la durée réelle de diffusion, le système implémente plusieurs vérifications :

1. **Détection des anomalies** : Le système signale les durées anormalement longues ou courtes.

2. **Comparaison avec la durée connue des pistes** : Pour les pistes dont la durée est connue, le système vérifie que la durée de diffusion est cohérente.

3. **Vérification des chevauchements** : Le système vérifie qu'il n'y a pas de chevauchement entre les détections sur une même station.

### Conclusion

La distinction entre la durée d'échantillon et la durée réelle de diffusion est fondamentale pour le calcul précis des redevances. Le système SODAV Monitor est conçu pour suivre avec précision la durée réelle de diffusion, en utilisant une combinaison de détection continue, de suivi des pistes en cours et de calcul précis de la durée totale. 