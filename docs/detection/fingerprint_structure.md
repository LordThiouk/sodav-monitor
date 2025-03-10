# Structure de Base de Données pour les Empreintes Digitales

Ce document détaille la nouvelle structure de base de données mise en place pour gérer les empreintes digitales multiples dans le système SODAV Monitor.

## Vue d'ensemble

La nouvelle structure permet de stocker plusieurs empreintes digitales pour chaque piste, ce qui améliore considérablement la robustesse et la précision de la détection locale. Elle prend également en charge différents types d'algorithmes d'empreintes (MD5, Chromaprint, etc.), offrant ainsi une plus grande flexibilité.

## Schéma de la Base de Données

### Table `tracks`

La table `tracks` a été modifiée pour inclure une colonne `chromaprint` et établir une relation avec la nouvelle table `fingerprints`.

```sql
CREATE TABLE tracks (
    id SERIAL PRIMARY KEY,
    title VARCHAR NOT NULL,
    artist_id INTEGER REFERENCES artists(id),
    isrc VARCHAR,
    label VARCHAR,
    album VARCHAR,
    duration INTERVAL,
    fingerprint VARCHAR UNIQUE,
    fingerprint_raw BYTEA,
    chromaprint VARCHAR,
    release_date VARCHAR,
    genre VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tracks_isrc ON tracks(isrc);
CREATE INDEX idx_tracks_title ON tracks(title);
CREATE INDEX idx_tracks_artist_id ON tracks(artist_id);
```

### Table `fingerprints`

Une nouvelle table `fingerprints` a été créée pour stocker les empreintes digitales multiples.

```sql
CREATE TABLE fingerprints (
    id SERIAL PRIMARY KEY,
    track_id INTEGER REFERENCES tracks(id) ON DELETE CASCADE,
    hash VARCHAR(255),
    raw_data BYTEA,
    offset FLOAT,
    algorithm VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fingerprints_track_id ON fingerprints(track_id);
CREATE INDEX idx_fingerprints_hash ON fingerprints(hash);
```

## Modèles SQLAlchemy

### Classe `Track`

```python
class Track(Base):
    """Track model."""
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    artist_id = Column(Integer, ForeignKey("artists.id"))
    isrc = Column(String, index=True)
    label = Column(String)
    album = Column(String)
    duration = Column(Interval)
    fingerprint = Column(String, unique=True)
    fingerprint_raw = Column(LargeBinary)
    chromaprint = Column(String, nullable=True)
    release_date = Column(String, nullable=True)
    genre = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    artist = relationship("Artist", back_populates="tracks")
    detections = relationship("TrackDetection", back_populates="track")
    stats = relationship("TrackStats", back_populates="track", uselist=False)
    fingerprints = relationship("Fingerprint", back_populates="track", cascade="all, delete-orphan")
```

### Classe `Fingerprint`

```python
class Fingerprint(Base):
    """Fingerprint model for storing multiple fingerprints per track."""
    __tablename__ = "fingerprints"
    
    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    hash = Column(String(255), index=True)
    raw_data = Column(LargeBinary)
    offset = Column(Float)  # Position dans la piste en secondes
    algorithm = Column(String(50))  # 'md5', 'chromaprint', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with Track
    track = relationship("Track", back_populates="fingerprints")
```

## Migration des Données

Un script de migration a été créé pour :
1. Ajouter la colonne `chromaprint` à la table `tracks`
2. Créer la table `fingerprints`
3. Migrer les empreintes existantes de la table `tracks` vers la nouvelle table `fingerprints`

Le script est disponible dans `backend/models/migrations/add_fingerprints_table.py`.

## Utilisation

### Création d'une Empreinte

```python
# Créer une nouvelle empreinte pour une piste existante
fingerprint = Fingerprint(
    track_id=track.id,
    hash="2121efb0f46e02f5cdf9...",
    raw_data=b"...",
    offset=0.0,
    algorithm="md5"
)
session.add(fingerprint)
session.commit()
```

### Récupération des Empreintes d'une Piste

```python
# Récupérer toutes les empreintes d'une piste
track = session.query(Track).filter_by(id=track_id).first()
fingerprints = track.fingerprints

# Afficher les détails des empreintes
for fp in fingerprints:
    print(f"Empreinte ID: {fp.id}")
    print(f"Hash: {fp.hash[:20]}...")
    print(f"Algorithme: {fp.algorithm}")
    print(f"Offset: {fp.offset}")
```

### Recherche par Empreinte

```python
# Rechercher une piste par son empreinte
fingerprint_hash = "2121efb0f46e02f5cdf9..."
fingerprint = session.query(Fingerprint).filter_by(hash=fingerprint_hash).first()

if fingerprint:
    track = fingerprint.track
    print(f"Piste trouvée: {track.title} par {track.artist.name}")
else:
    print("Aucune piste trouvée avec cette empreinte")
```

## Avantages de la Nouvelle Structure

1. **Flexibilité** : Possibilité de stocker plusieurs empreintes par piste, ce qui améliore la robustesse de la détection.
2. **Performance** : Indexation optimisée pour les recherches d'empreintes.
3. **Évolutivité** : Support pour différents types d'algorithmes d'empreintes.
4. **Précision** : Possibilité de stocker des empreintes pour différentes sections d'une piste.
5. **Maintenance** : Facilité de gestion et de mise à jour des empreintes.

## Prochaines Étapes

1. **Mise à jour du TrackManager** : Modifier la classe `TrackManager` pour utiliser la nouvelle table `fingerprints` lors de la détection locale.
2. **Implémentation de Chromaprint** : Intégrer l'algorithme Chromaprint pour générer des empreintes plus robustes.
3. **Extraction d'Empreintes Multiples** : Corriger le script `test_multi_fingerprint_detection.py` pour extraire correctement plusieurs empreintes à partir d'un fichier audio.
4. **Optimisation des Recherches** : Mettre en place des mécanismes de cache et de recherche parallèle pour améliorer les performances.
5. **Métriques de Détection** : Développer des outils pour mesurer et améliorer la précision de la détection locale.

## Conclusion

La nouvelle structure de base de données pour les empreintes digitales constitue une amélioration significative du système SODAV Monitor. Elle permet une détection locale plus robuste et précise, réduisant ainsi la dépendance aux services externes et améliorant l'efficacité globale du système. 