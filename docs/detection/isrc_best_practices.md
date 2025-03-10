# Bonnes Pratiques pour l'Utilisation des Codes ISRC

Ce document présente les bonnes pratiques pour l'utilisation des codes ISRC (International Standard Recording Code) dans le système de détection musicale SODAV Monitor.

## Qu'est-ce qu'un code ISRC ?

L'ISRC (International Standard Recording Code) est un identifiant unique pour les enregistrements sonores, standardisé par l'ISO 3901. Il est composé de 12 caractères alphanumériques et suit le format suivant :

```
CC-XXX-YY-NNNNN
```

Où :
- **CC** : Code pays (2 lettres)
- **XXX** : Code du propriétaire de l'enregistrement (3 caractères alphanumériques)
- **YY** : Année de référence (2 chiffres)
- **NNNNN** : Code de désignation (5 chiffres)

Exemple : `FR-Z03-14-00123`

## Importance des Codes ISRC

Les codes ISRC sont essentiels pour plusieurs raisons :

1. **Identification unique** : Ils permettent d'identifier de manière unique un enregistrement sonore, indépendamment de son titre ou de son artiste.
2. **Standard international** : Ils sont reconnus et utilisés par l'industrie musicale mondiale.
3. **Traçabilité** : Ils permettent de suivre l'utilisation d'un enregistrement à travers différentes plateformes et médias.
4. **Gestion des droits** : Ils facilitent la gestion des droits d'auteur et la distribution des redevances.
5. **Déduplication** : Ils permettent d'éviter les doublons dans les bases de données musicales.

## Implémentation dans SODAV Monitor

### 1. Stockage des Codes ISRC

Dans SODAV Monitor, les codes ISRC sont stockés dans la table `tracks` :

```python
class Track(Base):
    __tablename__ = "tracks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    artist_id = Column(Integer, ForeignKey("artists.id"))
    isrc = Column(String(12), unique=True, index=True)  # Contrainte d'unicité
    # ... autres champs
```

Points importants :
- La colonne `isrc` a une contrainte d'unicité (`unique=True`).
- La colonne est indexée pour des recherches rapides (`index=True`).
- La longueur est limitée à 12 caractères, conformément au standard.

### 2. Validation des Codes ISRC

Avant de sauvegarder un code ISRC, il est important de le valider :

```python
def validate_isrc(isrc):
    """Valide un code ISRC selon le format standard."""
    if not isrc:
        return False
    
    # Supprimer les tirets s'ils sont présents
    isrc = isrc.replace('-', '')
    
    # Vérifier la longueur
    if len(isrc) != 12:
        return False
    
    # Vérifier le format
    pattern = r'^[A-Z]{2}[A-Z0-9]{3}[0-9]{7}$'
    if not re.match(pattern, isrc):
        return False
    
    return True
```

### 3. Extraction des Codes ISRC

Les codes ISRC peuvent être extraits de différentes sources :

#### 3.1. AcoustID

```python
def extract_isrc_from_acoustid(acoustid_result):
    """Extrait le code ISRC d'un résultat AcoustID."""
    if not acoustid_result or 'recordings' not in acoustid_result:
        return None
    
    for recording in acoustid_result['recordings']:
        if 'isrc' in recording and recording['isrc']:
            # AcoustID peut retourner plusieurs ISRC, prendre le premier
            return recording['isrc'][0]
    
    return None
```

#### 3.2. AudD

```python
def extract_isrc_from_audd(audd_result):
    """Extrait le code ISRC d'un résultat AudD."""
    if not audd_result or 'result' not in audd_result:
        return None
    
    result = audd_result['result']
    
    # Vérifier directement dans le résultat
    if 'isrc' in result and result['isrc']:
        return result['isrc']
    
    # Vérifier dans les données Apple Music
    if 'apple_music' in result and 'isrc' in result['apple_music']:
        return result['apple_music']['isrc']
    
    return None
```

### 4. Utilisation des Codes ISRC pour la Déduplication

La déduplication basée sur l'ISRC est une pratique essentielle :

```python
async def find_track_by_metadata(self, metadata, station_id=None):
    """Recherche une piste par ses métadonnées, en priorisant l'ISRC."""
    # Vérifier d'abord par ISRC si disponible
    if 'isrc' in metadata and metadata['isrc']:
        isrc = metadata['isrc']
        
        # Valider l'ISRC
        if validate_isrc(isrc):
            # Rechercher une piste existante avec cet ISRC
            existing_track = self.db_session.query(Track).filter(Track.isrc == isrc).first()
            
            if existing_track:
                self.logger.info(f"Found existing track with ISRC {isrc}: {existing_track.title}")
                
                # Mettre à jour les statistiques si station_id est fourni
                if station_id:
                    play_duration = metadata.get('duration', 0)
                    self._record_play_time(station_id, existing_track.id, play_duration)
                
                # Retourner avec confiance maximale pour les correspondances ISRC
                return {
                    'track': self._track_to_dict(existing_track),
                    'confidence': 1.0,
                    'source': 'database',
                    'detection_method': 'isrc_match'
                }
    
    # Si pas d'ISRC ou pas de correspondance, continuer avec d'autres méthodes
    # ...
```

### 5. Mise à Jour des Statistiques pour les Pistes Existantes

Lorsqu'une piste est identifiée par son ISRC, il est important de mettre à jour ses statistiques de lecture plutôt que de créer une nouvelle piste :

```python
def _record_play_time(self, station_id, track_id, play_duration):
    """Enregistre le temps de lecture d'une piste sur une station."""
    try:
        # Créer une nouvelle détection
        detection = TrackDetection(
            track_id=track_id,
            station_id=station_id,
            detected_at=datetime.utcnow(),
            play_duration=timedelta(seconds=play_duration),
            confidence=1.0,  # Confiance maximale pour les correspondances ISRC
            detection_method="isrc_match"
        )
        self.db_session.add(detection)
        
        # Mettre à jour les statistiques de la station
        self._update_station_track_stats(station_id, track_id, timedelta(seconds=play_duration))
        
        self.db_session.commit()
        self.logger.info(f"Recorded play time for track ID {track_id} on station ID {station_id}: {play_duration} seconds")
    except Exception as e:
        self.logger.error(f"Error recording play time: {e}")
        self.db_session.rollback()
```

## Bonnes Pratiques

### 1. Prioriser la Recherche par ISRC

Toujours vérifier d'abord si une piste avec le même ISRC existe déjà avant de créer une nouvelle piste.

### 2. Valider les Codes ISRC

Toujours valider les codes ISRC avant de les sauvegarder pour s'assurer qu'ils respectent le format standard.

### 3. Standardiser le Format

Stocker les codes ISRC dans un format standardisé (sans tirets) pour faciliter les recherches.

### 4. Attribuer une Confiance Maximale

Attribuer un niveau de confiance maximal (1.0) aux correspondances par ISRC, car il s'agit d'un identifiant unique.

### 5. Mettre à Jour les Statistiques

Mettre à jour les statistiques de lecture pour les pistes existantes au lieu de créer des doublons.

### 6. Enrichir les Métadonnées

Si une piste est trouvée par son ISRC mais que certaines métadonnées sont manquantes, enrichir la piste existante avec les nouvelles métadonnées.

### 7. Gérer les Conflits

En cas de conflit (par exemple, deux pistes différentes avec le même ISRC), privilégier la piste avec les métadonnées les plus complètes.

### 8. Tester la Contrainte d'Unicité

Ajouter des tests spécifiques pour valider le bon fonctionnement de la contrainte d'unicité ISRC.

## Tests Recommandés

### 1. Test de la Contrainte d'Unicité

```python
def test_isrc_uniqueness_constraint(self):
    """Tester que la contrainte d'unicité ISRC est appliquée."""
    # Créer une première piste avec un ISRC
    track1 = Track(
        title="Test Track 1",
        artist_id=self.artist.id,
        isrc="FR1234567890",
        label="Test Label",
        album="Test Album"
    )
    self.db_session.add(track1)
    self.db_session.commit()

    # Tenter de créer une deuxième piste avec le même ISRC
    track2 = Track(
        title="Test Track 2",
        artist_id=self.artist.id,
        isrc="FR1234567890",
        label="Another Label",
        album="Another Album"
    )
    self.db_session.add(track2)
    
    # Vérifier que la contrainte d'unicité est appliquée
    with self.assertRaises(IntegrityError):
        self.db_session.commit()
```

### 2. Test de la Recherche par ISRC

```python
def test_find_track_by_isrc(self):
    """Tester la recherche d'une piste par ISRC."""
    # Créer une piste avec un ISRC unique
    test_isrc = f"FR{uuid.uuid4().hex[:10].upper()}"
    track = Track(
        title="Test Track",
        artist_id=self.artist.id,
        isrc=test_isrc,
        label="Test Label",
        album="Test Album"
    )
    self.db_session.add(track)
    self.db_session.commit()

    # Rechercher la piste par ISRC
    found_track = self.db_session.query(Track).filter(Track.isrc == test_isrc).first()
    
    # Vérifier que la piste est trouvée
    self.assertIsNotNone(found_track)
    self.assertEqual(found_track.title, "Test Track")
    self.assertEqual(found_track.isrc, test_isrc)
```

### 3. Test de la Mise à Jour des Statistiques

```python
def test_update_play_statistics(self):
    """Tester que les statistiques de lecture sont mises à jour pour les pistes existantes."""
    # Créer une piste avec un ISRC unique
    test_isrc = f"FR{uuid.uuid4().hex[:10].upper()}"
    track = Track(
        title="Test Track",
        artist_id=self.artist.id,
        isrc=test_isrc,
        label="Test Label",
        album="Test Album"
    )
    self.db_session.add(track)
    self.db_session.commit()

    # Créer une station pour les statistiques
    station_id = 1
    
    # Utiliser la méthode _record_play_time pour enregistrer une détection et mettre à jour les statistiques
    self.track_manager._record_play_time(station_id, track.id, 60)  # 60 secondes
    
    # Vérifier que les statistiques sont créées
    stats = self.db_session.query(StationTrackStats).filter(
        StationTrackStats.track_id == track.id,
        StationTrackStats.station_id == station_id
    ).first()
    
    self.assertIsNotNone(stats)
    self.assertEqual(stats.play_count, 1)
    self.assertEqual(stats.total_play_time.total_seconds(), 60)
    
    # Enregistrer une deuxième détection
    self.track_manager._record_play_time(station_id, track.id, 120)  # 120 secondes
    
    # Vérifier que les statistiques sont mises à jour
    stats = self.db_session.query(StationTrackStats).filter(
        StationTrackStats.track_id == track.id,
        StationTrackStats.station_id == station_id
    ).first()
    
    self.assertIsNotNone(stats)
    self.assertEqual(stats.play_count, 2)
    self.assertEqual(stats.total_play_time.total_seconds(), 180)  # 60 + 120 = 180 secondes
```

## Conclusion

L'utilisation efficace des codes ISRC est essentielle pour maintenir l'intégrité des données dans le système SODAV Monitor. En suivant ces bonnes pratiques, vous pouvez garantir que chaque enregistrement musical n'est représenté qu'une seule fois dans la base de données, ce qui permet d'obtenir des statistiques de lecture précises et des rapports fiables. 