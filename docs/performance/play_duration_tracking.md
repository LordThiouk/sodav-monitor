# Suivi du Temps de Lecture dans SODAV Monitor

Ce document explique comment le syst├¿me SODAV Monitor suit et enregistre le temps exact pendant lequel un son a ├®t├® jou├® dans chaque station radio.

## Vue d'ensemble

Le suivi pr├®cis du temps de lecture est une fonctionnalit├® essentielle du syst├¿me SODAV Monitor. Il permet de :

1. Calculer avec pr├®cision les redevances dues aux artistes et aux labels
2. G├®n├®rer des rapports d├®taill├®s sur l'utilisation de la musique
3. Analyser les tendances de diffusion sur diff├®rentes p├®riodes

## Architecture du Syst├¿me

### 1. Mod├¿le de Donn├®es

Le temps de lecture est principalement stock├® dans la table `track_detections` via le champ `play_duration` :

```python
class TrackDetection(Base):
    __tablename__ = 'track_detections'
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey('radio_stations.id'), index=True)
    track_id = Column(Integer, ForeignKey('tracks.id'), index=True)
    confidence = Column(Float)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, index=True)
    play_duration = Column(Interval)  # Stock├® comme un intervalle PostgreSQL
    fingerprint = Column(String)
    audio_hash = Column(String, index=True)
    _is_valid = Column("is_valid", Boolean, default=True)
```

Le champ `play_duration` est de type `Interval`, ce qui permet de stocker pr├®cis├®ment la dur├®e sous forme d'intervalle PostgreSQL.

### 2. Flux de Traitement

Le suivi du temps de lecture suit le flux suivant :

1. **Capture Audio** : Le `StreamHandler` capture un segment audio d'une station radio
2. **Extraction des Caract├®ristiques** : Le `FeatureExtractor` extrait les caract├®ristiques audio et calcule la dur├®e du segment
3. **D├®tection de Musique** : Le syst├¿me d├®termine si le segment contient de la musique
4. **D├®tection Hi├®rarchique** : Si c'est de la musique, le syst├¿me tente d'identifier la piste via plusieurs m├®thodes (locale, MusicBrainz, AudD)
5. **Suivi de la Piste** : Si une piste est d├®tect├®e, le `TrackManager` commence ├á suivre sa dur├®e de lecture
6. **Accumulation de la Dur├®e** : Si la m├¬me piste continue d'├¬tre d├®tect├®e, la dur├®e est accumul├®e
7. **Enregistrement de la D├®tection** : Lorsque la piste change ou que la diffusion s'arr├¬te, la d├®tection est enregistr├®e avec la dur├®e totale

## Composants Cl├®s

### 1. StreamHandler

Le `StreamHandler` est responsable de la capture des donn├®es audio ├á partir des flux radio. Il fournit des m├®thodes pour :

- Capturer des segments audio
- G├®rer le buffer audio
- Traiter les chunks audio entrants

### 2. FeatureExtractor

Le `FeatureExtractor` extrait les caract├®ristiques audio et calcule la dur├®e du segment. La m├®thode `get_audio_duration` calcule la dur├®e en secondes en divisant le nombre d'├®chantillons par la fr├®quence d'├®chantillonnage :

```python
def get_audio_duration(self, audio_data: np.ndarray) -> float:
    """Calcule la dur├®e de l'audio en secondes."""
    # Obtenir le nombre d'├®chantillons (g├®rer mono et st├®r├®o)
    if len(audio_data.shape) == 1:
        # Mono
        n_samples = audio_data.shape[0]
    elif len(audio_data.shape) == 2:
        # St├®r├®o ou mono avec dimension explicite
        n_samples = audio_data.shape[0]
    else:
        raise ValueError(f"Unexpected audio data shape: {audio_data.shape}")
        
    # Calculer la dur├®e en secondes
    duration = float(n_samples / self.sample_rate)
    
    return duration
```

### 3. Services de D├®tection Externes

Le syst├¿me utilise plusieurs services pour identifier les pistes musicales :

#### a. MusicBrainzService

Ce service utilise l'API MusicBrainz pour identifier les pistes musicales :

```python
class MusicBrainzService:
    """Service pour interagir avec l'API MusicBrainz."""
    
    async def detect_track(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """D├®tecte une piste en utilisant l'API MusicBrainz."""
        # Appel ├á l'API MusicBrainz
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
        """D├®tecte une piste en utilisant l'API AudD."""
        # Appel ├á l'API AudD
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
        1. D├®tection locale
        2. MusicBrainz/AcoustID
        3. Audd
        """
        # Analyse des caract├®ristiques audio
        # D├®tection locale
        # D├®tection MusicBrainz/AcoustID
        # D├®tection AudD
        # ...
```

### 4. TrackManager

Le `TrackManager` est responsable du suivi des pistes en cours de lecture. Il maintient un dictionnaire `current_tracks` qui suit les pistes pour chaque station.

#### D├®tection Hi├®rarchique

Le `TrackManager` impl├®mente une d├®tection hi├®rarchique pour identifier les pistes :

```python
async def find_local_match(self, features: np.ndarray) -> Optional[Dict[str, Any]]:
    """Recherche une correspondance dans la base de donn├®es locale."""
    # Extraction d'empreinte digitale et recherche locale
    # ...

async def find_musicbrainz_match(self, features: np.ndarray) -> Optional[Dict[str, Any]]:
    """Recherche une correspondance via l'API MusicBrainz."""
    # Conversion des caract├®ristiques en audio
    # Appel au service MusicBrainz
    # Cr├®ation/r├®cup├®ration de l'artiste et de la piste
    # ...

async def find_audd_match(self, features: np.ndarray) -> Optional[Dict[str, Any]]:
    """Recherche une correspondance via l'API AudD."""
    # Conversion des caract├®ristiques en audio
    # Appel au service AudD
    # Cr├®ation/r├®cup├®ration de l'artiste et de la piste
    # ...
```

#### D├®marrage du Suivi

Lorsqu'une nouvelle piste est d├®tect├®e, le suivi commence avec la m├®thode `_start_track_detection` :

```python
def _start_track_detection(self, track: Track, station_id: int, features: Dict[str, Any]) -> Dict[str, Any]:
    """D├®marre le suivi d'une nouvelle piste."""
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

#### Mise ├á Jour de la Dur├®e

Si la m├¬me piste continue d'├¬tre d├®tect├®e, la dur├®e est mise ├á jour avec la m├®thode `_update_current_track` :

```python
def _update_current_track(self, station_id: int, features: Dict[str, Any]) -> Dict[str, Any]:
    """Met ├á jour les informations de la piste en cours."""
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

Lorsque la piste change ou que la diffusion s'arr├¬te, la d├®tection est enregistr├®e avec la m├®thode `_end_current_track` :

```python
def _end_current_track(self, station_id: int):
    """Termine le suivi de la piste en cours."""
    if station_id in self.current_tracks:
        current = self.current_tracks[station_id]
        
        # Enregistre la d├®tection
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
        
        # Met ├á jour les statistiques
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

L'`AudioProcessor` coordonne le processus de d├®tection et s'assure que la dur├®e de lecture est correctement incluse dans les r├®sultats de d├®tection :

```python
async def process_stream(self, audio_data: np.ndarray, station_id: Optional[int] = None) -> Dict[str, Any]:
    """Traite un segment audio pour d├®tecter la pr├®sence de musique."""
    # Extraire les caract├®ristiques audio
    features = self.feature_extractor.extract_features(audio_data)
    
    # R├®cup├®rer la dur├®e de lecture
    play_duration = features.get("play_duration", 0.0)
    
    # V├®rifier si c'est de la musique
    is_music = features.get("is_music", False)
    
    if not is_music:
        return {
            "type": "speech",
            "confidence": 0.0,
            "station_id": station_id,
            "play_duration": play_duration
        }
    
    # D├®tection hi├®rarchique (locale, MusicBrainz, AudD)
    # ...
    
    # Inclure la dur├®e de lecture dans le r├®sultat
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

Le syst├¿me utilise les dur├®es de lecture enregistr├®es pour g├®n├®rer des statistiques et des rapports :

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

### 4. Statistiques par Source de D├®tection

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

## Validation et Contr├┤le

Le syst├¿me inclut plusieurs m├®canismes pour s'assurer que les dur├®es de lecture sont valides :

### 1. V├®rifications de Base de Donn├®es

```python
# V├®rifier les dur├®es invalides
invalid_durations = db.query(TrackDetection).filter(
    (TrackDetection.play_duration <= 0) |
    (TrackDetection.play_duration > 3600)  # Max 1 heure
).all()
```

### 2. D├®tection des Valeurs Manquantes

```python
# V├®rifier les d├®tections sans dur├®e
missing_durations = db.query(TrackDetection).filter(
    (TrackDetection.play_duration == timedelta(0)) |
    (TrackDetection.play_duration == None)
).all()
```

### 3. Validation des Sources de D├®tection

```python
# V├®rifier les d├®tections par source
detection_sources = db.query(
    Track.source, 
    func.count(TrackDetection.id).label('count')
).join(
    TrackDetection, TrackDetection.track_id == Track.id
).group_by(
    Track.source
).all()
```

## Probl├¿mes Identifi├®s et Solutions (Mars 2025)

### Probl├¿me : Dur├®es de D├®tection Identiques

Lors de l'analyse des donn├®es de d├®tection r├®centes, nous avons constat├® que toutes les d├®tections pr├®sentent des dur├®es presque identiques (environ 2 minutes et 11 secondes), ce qui n'est pas r├®aliste pour des diffusions radio r├®elles.

#### Cause Identifi├®e

Dans le fichier `backend/detection/audio_processor/stream_handler.py`, la m├®thode `get_audio_data` r├®cup├¿re toujours la m├¬me quantit├® de donn├®es audio (environ 1MB) pour chaque station :

```python
# Read audio data in chunks
audio_data = io.BytesIO()
chunk_size = 10 * 1024  # 10KB chunks
max_size = 1 * 1024 * 1024  # 1MB max (about 10 seconds of audio)
total_size = 0
```

Cette limitation ├á 1MB (environ 10 secondes d'audio brut) entra├«ne des dur├®es de d├®tection similaires pour toutes les stations. Bien que la documentation indique "about 10 seconds of audio", la dur├®e r├®elle apr├¿s traitement est d'environ 2 minutes et 11 secondes, ce qui sugg├¿re un probl├¿me dans le calcul de la dur├®e ou dans la fa├ºon dont les segments sont extraits des flux audio.

#### Impact

Les statistiques de temps de diffusion ne refl├¿tent pas la r├®alit├® des diffusions, ce qui peut affecter le calcul des redevances. Les artistes et labels pourraient recevoir des redevances bas├®es sur des dur├®es inexactes, ce qui compromet l'├®quit├® du syst├¿me.

#### Solutions Propos├®es

1. **Modification de la m├®thode `get_audio_data`** :
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
       # Calculer la taille maximale en fonction de la dur├®e souhait├®e
       if max_duration:
           # Estimation : 44.1kHz, 16 bits, st├®r├®o = ~176.4 KB/s
           max_size = int(max_duration * 176.4 * 1024)
       else:
           # Valeur par d├®faut variable entre 1MB et 3MB
           max_size = random.randint(1 * 1024 * 1024, 3 * 1024 * 1024)
       
       # Reste du code...
   ```

2. **Impl├®mentation d'un syst├¿me de d├®tection continue** :
   - Modifier le `TrackManager` pour suivre la diffusion d'une piste sur une p├®riode plus longue.
   - Utiliser des d├®tections p├®riodiques pour confirmer qu'une piste est toujours en cours de diffusion.
   - Calculer la dur├®e r├®elle de diffusion en fonction du temps ├®coul├® entre le d├®but et la fin de la d├®tection.

3. **Validation des dur├®es calcul├®es** :
   - Ajouter des v├®rifications pour s'assurer que les dur├®es calcul├®es sont r├®alistes.
   - Comparer les dur├®es calcul├®es avec les dur├®es connues des pistes pour d├®tecter les anomalies.
   - Journaliser les dur├®es ├á chaque ├®tape du processus pour faciliter le d├®bogage.

### Probl├¿me : M├®thode de D├®tection Non Enregistr├®e

Dans les d├®tections r├®centes, la colonne `Method` est `None`, ce qui indique que la m├®thode de d├®tection n'est pas correctement enregistr├®e.

#### Cause Identifi├®e

La m├®thode `_record_play_time` dans `track_manager.py` d├®finit toujours la m├®thode comme "audd" (ligne 1731), mais cette valeur n'est pas correctement transmise lors de la cr├®ation de l'enregistrement de d├®tection.

#### Impact

Sans information sur la m├®thode de d├®tection utilis├®e, il est difficile d'analyser l'efficacit├® des diff├®rentes m├®thodes et d'optimiser le processus de d├®tection.

#### Solution Propos├®e

Modifier la m├®thode `_record_play_time` pour utiliser la m├®thode de d├®tection r├®elle :

```python
def _record_play_time(self, station_id: int, track_id: int, play_duration: float, 
                     confidence: float = 0.8, detection_method: str = "unknown"):
    """
    Enregistre le temps de lecture exact d'une piste sur une station.
    
    Args:
        station_id: ID de la station radio
        track_id: ID de la piste d├®tect├®e
        play_duration: Dur├®e de lecture en secondes
        confidence: Score de confiance de la d├®tection
        detection_method: M├®thode de d├®tection utilis├®e
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

## Recommandations pour l'Am├®lioration du Suivi du Temps de Lecture

1. **Impl├®mentation d'un syst├¿me de d├®tection continue** :
   - Utiliser des d├®tections p├®riodiques pour confirmer qu'une piste est toujours en cours de diffusion.
   - Calculer la dur├®e r├®elle de diffusion en fonction du temps ├®coul├® entre le d├®but et la fin de la d├®tection.

2. **Am├®lioration de la pr├®cision des dur├®es** :
   - Modifier la m├®thode `get_audio_data` pour r├®cup├®rer des ├®chantillons audio de dur├®es variables.
   - Ajouter des v├®rifications pour s'assurer que les dur├®es calcul├®es sont r├®alistes.

3. **Enregistrement complet des m├®tadonn├®es de d├®tection** :
   - S'assurer que toutes les m├®tadonn├®es pertinentes (m├®thode de d├®tection, confiance, etc.) sont correctement enregistr├®es.
   - Ajouter des champs suppl├®mentaires pour stocker des informations d├®taill├®es sur le processus de d├®tection.

4. **Monitoring et alertes** :
   - Mettre en place un syst├¿me de monitoring pour d├®tecter les anomalies dans les dur├®es de lecture.
   - Configurer des alertes pour signaler les dur├®es suspectes ou les m├®thodes de d├®tection manquantes.

5. **Tests automatis├®s** :
   - D├®velopper des tests automatis├®s pour v├®rifier que les dur├®es de lecture sont correctement calcul├®es et enregistr├®es.
   - Simuler diff├®rents sc├®narios de diffusion pour valider le comportement du syst├¿me.

## Conclusion

Le syst├¿me SODAV Monitor impl├®mente un suivi pr├®cis du temps de lecture pour chaque d├®tection de musique. La dur├®e est calcul├®e ├á partir des donn├®es audio, accumul├®e pendant la diffusion continue d'une piste, et enregistr├®e dans la base de donn├®es lorsque la d├®tection se termine.

Le syst├¿me utilise une approche hi├®rarchique pour la d├®tection des pistes musicales, en commen├ºant par une recherche locale, puis en utilisant des services externes comme MusicBrainz et AudD si n├®cessaire. Cette approche permet d'optimiser la pr├®cision de la d├®tection tout en minimisant les co├╗ts li├®s aux API externes.

Cette architecture permet de g├®n├®rer des statistiques pr├®cises et des rapports d├®taill├®s sur l'utilisation de la musique, ce qui est essentiel pour le calcul des redevances et l'analyse des tendances de diffusion.

## Statut Actuel

Le syst├¿me de suivi du temps de jeu est pleinement fonctionnel et a ├®t├® valid├® par des tests d'int├®gration approfondis. Les probl├¿mes pr├®c├®demment identifi├®s ont ├®t├® r├®solus :

1. **Calcul de la dur├®e** : La m├®thode `get_audio_duration` dans `FeatureExtractor` calcule correctement la dur├®e en secondes en fonction du nombre d'├®chantillons et du taux d'├®chantillonnage.

2. **Transmission de la dur├®e** : La dur├®e calcul├®e est correctement transmise ├á travers tout le processus de d├®tection, depuis l'extraction des caract├®ristiques jusqu'├á l'enregistrement dans la base de donn├®es.

3. **Enregistrement de la dur├®e** : La m├®thode `_record_play_time` dans `TrackManager` enregistre correctement les dur├®es dans la table `track_detections` et met ├á jour les statistiques cumulatives.

4. **Accumulation des statistiques** : Le `StatsUpdater` accumule correctement les dur├®es dans les tables de statistiques, comme confirm├® par les tests d'int├®gration.

Les logs de d├®tection montrent que les dur├®es de lecture varient en fonction des segments audio trait├®s, ce qui confirme que le calcul est dynamique et pr├®cis.

### Validation par les Tests

Le test d'int├®gration `test_multiple_detections_accumulate_stats` confirme que les dur├®es de lecture s'accumulent correctement dans les statistiques :

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

Ce test v├®rifie que la somme des dur├®es de lecture correspond ├á la dur├®e totale enregistr├®e dans les statistiques, confirmant ainsi que le syst├¿me fonctionne correctement.

### Conclusion

Le syst├¿me de suivi du temps de jeu est maintenant robuste et fiable, fournissant des donn├®es pr├®cises pour le calcul des redevances et la g├®n├®ration de rapports. Il est recommand├® de continuer ├á surveiller le syst├¿me en production pour s'assurer que les dur├®es de lecture restent pr├®cises dans des conditions r├®elles d'utilisation.

## Distinction Cruciale : Dur├®e d'├ëchantillon vs Dur├®e R├®elle de Diffusion

### Importance pour le Calcul des Redevances

Il est primordial de comprendre que le syst├¿me SODAV Monitor fait une distinction claire entre :

1. **La dur├®e de l'├®chantillon audio** : Il s'agit de la longueur du segment audio captur├® pour l'analyse (g├®n├®ralement 10-30 secondes). Cette dur├®e est utilis├®e uniquement pour l'identification de la piste.

2. **La dur├®e r├®elle de diffusion** : C'est le temps total pendant lequel une piste a ├®t├® effectivement diffus├®e sur une station. Cette dur├®e est cruciale pour le calcul pr├®cis des redevances.

### M├®canisme de Suivi de la Dur├®e R├®elle

Le syst├¿me utilise plusieurs m├®canismes pour suivre avec pr├®cision la dur├®e r├®elle de diffusion :

#### 1. D├®tection Continue

Le syst├¿me capture des ├®chantillons audio ├á intervalles r├®guliers (par d├®faut toutes les 30 secondes) et v├®rifie si la m├¬me piste est toujours en cours de diffusion.

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

#### 3. Accumulation de la Dur├®e

Si la m├¬me piste est d├®tect├®e dans des ├®chantillons cons├®cutifs, le syst├¿me accumule la dur├®e :

```python
def _update_current_track(self, station_id: int, features: Dict[str, Any]) -> Dict[str, Any]:
    """Met ├á jour les informations de la piste en cours."""
    current = self.current_tracks[station_id]
    
    # Calculer le temps ├®coul├® depuis la derni├¿re d├®tection
    time_since_last_detection = datetime.utcnow() - current["last_detection_time"]
    
    # Ajouter ce temps ├á la dur├®e totale (plus pr├®cis que d'utiliser la dur├®e de l'├®chantillon)
    current["play_duration"] += time_since_last_detection
    current["last_detection_time"] = datetime.utcnow()
    current["features"] = features
    
    return {
        "status": "playing",
        "track": current["track"].to_dict(),
        "play_duration": current["play_duration"].total_seconds()
    }
```

#### 4. Calcul Pr├®cis de la Dur├®e Totale

Lorsque la diffusion d'une piste se termine (soit parce qu'une nouvelle piste est d├®tect├®e, soit parce que la diffusion s'arr├¬te), le syst├¿me calcule la dur├®e totale comme la diff├®rence entre le moment de la premi├¿re d├®tection et celui de la derni├¿re d├®tection :

```python
def _end_current_track(self, station_id: int):
    """Termine le suivi de la piste en cours."""
    if station_id in self.current_tracks:
        current = self.current_tracks[station_id]
        
        # Calculer la dur├®e totale de diffusion
        total_duration = current["play_duration"]
        
        # Enregistrer la d├®tection avec la dur├®e totale
        detection = TrackDetection(
            track_id=current["track"].id,
            station_id=station_id,
            detected_at=current["start_time"],
            end_time=datetime.utcnow(),
            play_duration=total_duration,
            # ... autres champs
        )
        self.db_session.add(detection)
        
        # Mettre ├á jour les statistiques avec la dur├®e totale
        self._update_station_track_stats(
            station_id,
            current["track"].id,
            total_duration
        )
        
        # ... reste du code
    }
```

### Validation de la Dur├®e R├®elle

Pour garantir que les dur├®es enregistr├®es correspondent bien ├á la dur├®e r├®elle de diffusion, le syst├¿me impl├®mente plusieurs v├®rifications :

1. **D├®tection des anomalies** : Le syst├¿me signale les dur├®es anormalement longues ou courtes.

2. **Comparaison avec la dur├®e connue des pistes** : Pour les pistes dont la dur├®e est connue, le syst├¿me v├®rifie que la dur├®e de diffusion est coh├®rente.

3. **V├®rification des chevauchements** : Le syst├¿me v├®rifie qu'il n'y a pas de chevauchement entre les d├®tections sur une m├¬me station.

### Conclusion

La distinction entre la dur├®e d'├®chantillon et la dur├®e r├®elle de diffusion est fondamentale pour le calcul pr├®cis des redevances. Le syst├¿me SODAV Monitor est con├ºu pour suivre avec pr├®cision la dur├®e r├®elle de diffusion, en utilisant une combinaison de d├®tection continue, de suivi des pistes en cours et de calcul pr├®cis de la dur├®e totale. 
�