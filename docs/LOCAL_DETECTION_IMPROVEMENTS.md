# Améliorations de la Détection Locale avec Empreintes Digitales

Ce document présente des recommandations détaillées pour améliorer le système de détection locale basé sur les empreintes digitales (fingerprints) dans le projet SODAV Monitor.

## 1. État actuel du système

### 1.1. Processus de détection locale

Le système actuel utilise une approche hiérarchique pour la détection des pistes musicales :

1. **Détection locale** : Recherche d'une correspondance dans la base de données locale en utilisant les empreintes digitales.
2. **Services externes** : Si la détection locale échoue, le système fait appel à des services externes (AcoustID, AudD).

La détection locale est implémentée dans la méthode `find_local_match` de la classe `TrackManager` et suit ces étapes :
- Extraction de l'empreinte digitale à partir des caractéristiques audio
- Recherche d'une correspondance exacte dans la base de données
- Si aucune correspondance exacte n'est trouvée, calcul de la similarité avec toutes les pistes existantes
- Retour de la meilleure correspondance si le score de similarité dépasse un seuil (0.7)

### 1.2. Génération des empreintes digitales

Les empreintes digitales sont générées dans la méthode `_extract_fingerprint` de la classe `TrackManager` :
- Utilisation des caractéristiques MFCC, chroma et centroïde spectral
- Conversion en chaîne JSON et calcul d'un hash MD5
- Stockage du hash (pour la recherche) et des données brutes (pour la comparaison)

### 1.3. Limitations actuelles

- **Performance** : La recherche de similarité parcourt toutes les pistes de la base de données, ce qui peut devenir inefficace avec un grand nombre de pistes.
- **Précision** : L'approche actuelle basée sur MD5 ne permet pas une recherche approximative efficace.
- **Robustesse** : Les empreintes ne sont pas suffisamment robustes aux variations de qualité audio, de volume, etc.
- **Indexation** : Absence d'indexation optimisée pour les recherches d'empreintes.

## 2. Recommandations d'amélioration

### 2.1. Utilisation d'algorithmes spécialisés

#### 2.1.1. Intégration de Chromaprint/AcoustID

**Recommandation** : Intégrer l'algorithme Chromaprint (utilisé par AcoustID) pour la génération d'empreintes locales.

**Implémentation** :
```python
def generate_chromaprint(audio_data: bytes) -> str:
    """Génère une empreinte Chromaprint à partir des données audio."""
    import subprocess
    import tempfile
    
    # Écrire les données audio dans un fichier temporaire
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_file.write(audio_data)
        temp_path = temp_file.name
    
    try:
        # Appeler fpcalc (outil Chromaprint)
        result = subprocess.run(
            ['fpcalc', '-raw', temp_path],
            capture_output=True,
            text=True
        )
        
        # Extraire l'empreinte
        for line in result.stdout.splitlines():
            if line.startswith('FINGERPRINT='):
                return line[12:]
        
        return None
    finally:
        # Supprimer le fichier temporaire
        os.unlink(temp_path)
```

**Avantages** :
- Algorithme éprouvé et optimisé pour la reconnaissance musicale
- Compatible avec AcoustID pour les recherches externes
- Robuste aux variations de qualité audio

#### 2.1.2. Implémentation de l'algorithme Dejavu

**Recommandation** : Implémenter l'algorithme Dejavu pour la génération et la recherche d'empreintes.

**Implémentation** :
```python
class DejavuFingerprinter:
    def __init__(self):
        self.sample_rate = 44100
        self.window_size = 4096
        self.overlap_ratio = 0.5
        self.fan_value = 15
        self.amp_min = 10
        
    def fingerprint(self, audio_data: np.ndarray) -> List[Tuple[str, int]]:
        """Génère des empreintes Dejavu à partir des données audio."""
        # Calculer le spectrogramme
        spectrum = self._spectrum(audio_data)
        
        # Trouver les pics
        peaks = self._find_peaks(spectrum)
        
        # Générer les empreintes
        return self._generate_fingerprints(peaks)
```

**Avantages** :
- Optimisé pour la recherche locale rapide
- Permet la reconnaissance de fragments courts
- Robuste au bruit et aux distorsions

### 2.2. Optimisation de la base de données

#### 2.2.1. Indexation des empreintes

**Recommandation** : Créer une table dédiée pour les empreintes digitales avec des index optimisés.

**Implémentation** :
```python
# Dans models.py
class Fingerprint(Base):
    __tablename__ = 'fingerprints'
    
    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id'), index=True)
    hash = Column(String(255), index=True)
    offset = Column(Integer)
    
    # Relation avec Track
    track = relationship("Track", back_populates="fingerprints")

# Dans Track
fingerprints = relationship("Fingerprint", back_populates="track", cascade="all, delete-orphan")
```

**Avantages** :
- Recherche beaucoup plus rapide grâce aux index
- Possibilité de stocker plusieurs empreintes par piste
- Meilleure organisation des données

#### 2.2.2. Utilisation d'une base de données spécialisée

**Recommandation** : Pour les grands volumes de données, envisager l'utilisation d'une base de données spécialisée comme Elasticsearch ou FAISS.

**Implémentation** :
```python
from elasticsearch import Elasticsearch

class ElasticsearchFingerprinter:
    def __init__(self, es_host='localhost:9200'):
        self.es = Elasticsearch([es_host])
        
    def index_fingerprint(self, track_id: int, fingerprint: str):
        """Indexe une empreinte dans Elasticsearch."""
        self.es.index(
            index='fingerprints',
            body={
                'track_id': track_id,
                'fingerprint': fingerprint
            }
        )
        
    def search_fingerprint(self, fingerprint: str) -> List[Dict]:
        """Recherche une empreinte dans Elasticsearch."""
        result = self.es.search(
            index='fingerprints',
            body={
                'query': {
                    'fuzzy': {
                        'fingerprint': {
                            'value': fingerprint,
                            'fuzziness': 2
                        }
                    }
                }
            }
        )
        
        return result['hits']['hits']
```

**Avantages** :
- Recherche approximative très rapide
- Passage à l'échelle pour des millions d'empreintes
- Fonctionnalités avancées de recherche

### 2.3. Amélioration de la robustesse

#### 2.3.1. Empreintes multiples par piste

**Recommandation** : Stocker plusieurs empreintes pour chaque piste, représentant différentes sections ou qualités.

**Implémentation** :
```python
def extract_multiple_fingerprints(audio_data: bytes, num_segments: int = 5) -> List[str]:
    """Extrait plusieurs empreintes à partir de différentes sections de l'audio."""
    # Convertir les données audio en tableau numpy
    audio_array = audio_to_numpy(audio_data)
    
    # Calculer la longueur de chaque segment
    segment_length = len(audio_array) // num_segments
    
    # Extraire une empreinte pour chaque segment
    fingerprints = []
    for i in range(num_segments):
        start = i * segment_length
        end = start + segment_length
        segment = audio_array[start:end]
        fingerprint = generate_fingerprint(segment)
        fingerprints.append(fingerprint)
    
    return fingerprints
```

**Avantages** :
- Meilleure robustesse aux variations de position dans la piste
- Possibilité de reconnaître une piste à partir d'un fragment court
- Augmentation du taux de détection locale

#### 2.3.2. Normalisation des caractéristiques audio

**Recommandation** : Normaliser les caractéristiques audio avant la génération d'empreintes pour améliorer la robustesse.

**Implémentation** :
```python
def normalize_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise les caractéristiques audio pour améliorer la robustesse."""
    normalized = {}
    
    # Normaliser les MFCC
    if "mfcc_mean" in features:
        mfcc = np.array(features["mfcc_mean"])
        normalized["mfcc_mean"] = (mfcc - np.mean(mfcc)) / np.std(mfcc)
    
    # Normaliser le chroma
    if "chroma_mean" in features:
        chroma = np.array(features["chroma_mean"])
        normalized["chroma_mean"] = chroma / np.sum(chroma) if np.sum(chroma) > 0 else chroma
    
    # Autres caractéristiques...
    
    return normalized
```

**Avantages** :
- Robustesse aux variations de volume
- Meilleure comparaison entre différentes qualités d'enregistrement
- Réduction des faux négatifs

### 2.4. Optimisation des performances

#### 2.4.1. Mise en cache des empreintes

**Recommandation** : Mettre en cache les empreintes fréquemment utilisées pour accélérer la détection.

**Implémentation** :
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_track_by_fingerprint(fingerprint_hash: str) -> Optional[int]:
    """Récupère l'ID d'une piste à partir de son empreinte (avec cache)."""
    # Recherche dans la base de données
    fingerprint = db_session.query(Fingerprint).filter_by(hash=fingerprint_hash).first()
    
    return fingerprint.track_id if fingerprint else None
```

**Avantages** :
- Réduction significative du temps de recherche pour les pistes populaires
- Diminution de la charge sur la base de données
- Amélioration des performances globales

#### 2.4.2. Recherche parallèle

**Recommandation** : Implémenter une recherche parallèle pour les grandes bases de données d'empreintes.

**Implémentation** :
```python
async def find_local_match_parallel(fingerprint: str, chunk_size: int = 1000) -> Optional[Dict]:
    """Recherche une correspondance locale en parallèle."""
    # Récupérer le nombre total d'empreintes
    total = db_session.query(func.count(Fingerprint.id)).scalar()
    
    # Calculer le nombre de chunks
    num_chunks = (total + chunk_size - 1) // chunk_size
    
    # Créer les tâches de recherche
    tasks = []
    for i in range(num_chunks):
        offset = i * chunk_size
        tasks.append(search_fingerprint_chunk(fingerprint, offset, chunk_size))
    
    # Exécuter les tâches en parallèle
    results = await asyncio.gather(*tasks)
    
    # Trouver la meilleure correspondance
    best_match = None
    best_score = 0.0
    
    for result in results:
        if result and result["score"] > best_score:
            best_match = result
            best_score = result["score"]
    
    return best_match
```

**Avantages** :
- Recherche beaucoup plus rapide dans les grandes bases de données
- Utilisation efficace des ressources multi-cœurs
- Possibilité de distribuer la recherche sur plusieurs serveurs

## 3. Plan d'implémentation

### 3.1. Phase 1 : Amélioration de la génération d'empreintes

1. Intégrer l'algorithme Chromaprint pour la génération d'empreintes
2. Mettre à jour la méthode `_extract_fingerprint` pour utiliser Chromaprint
3. Ajouter la normalisation des caractéristiques audio
4. Mettre en place des tests pour valider la qualité des empreintes

### 3.2. Phase 2 : Optimisation de la base de données

1. Créer une table dédiée pour les empreintes digitales
2. Migrer les empreintes existantes vers la nouvelle structure
3. Ajouter des index optimisés
4. Mettre à jour les méthodes de recherche pour utiliser la nouvelle structure

### 3.3. Phase 3 : Amélioration de la robustesse

1. Implémenter l'extraction d'empreintes multiples par piste
2. Ajouter la normalisation des caractéristiques audio
3. Mettre en place des tests de robustesse avec différentes qualités audio

### 3.4. Phase 4 : Optimisation des performances

1. Implémenter le cache d'empreintes
2. Ajouter la recherche parallèle
3. Optimiser les requêtes à la base de données
4. Mettre en place des tests de performance

## 4. Exemples d'utilisation

### 4.1. Détection locale améliorée

```python
async def detect_track(audio_data: bytes) -> Dict[str, Any]:
    """Détecte une piste à partir de données audio."""
    # Générer les empreintes
    fingerprints = extract_multiple_fingerprints(audio_data)
    
    # Rechercher des correspondances pour chaque empreinte
    matches = []
    for fingerprint in fingerprints:
        match = await find_local_match(fingerprint)
        if match:
            matches.append(match)
    
    # Si des correspondances ont été trouvées, retourner la meilleure
    if matches:
        # Trier par score de confiance
        matches.sort(key=lambda m: m["confidence"], reverse=True)
        return {
            "success": True,
            "detection": matches[0],
            "source": "local"
        }
    
    # Si aucune correspondance locale, utiliser les services externes
    return await detect_with_external_services(audio_data)
```

### 4.2. Mise à jour des empreintes existantes

```python
async def update_track_fingerprints(track_id: int):
    """Met à jour les empreintes d'une piste existante."""
    # Récupérer la piste
    track = db_session.query(Track).filter_by(id=track_id).first()
    if not track:
        return False
    
    # Récupérer les données audio
    audio_data = get_track_audio(track_id)
    if not audio_data:
        return False
    
    # Supprimer les anciennes empreintes
    db_session.query(Fingerprint).filter_by(track_id=track_id).delete()
    
    # Générer de nouvelles empreintes
    fingerprints = extract_multiple_fingerprints(audio_data)
    
    # Enregistrer les nouvelles empreintes
    for i, fingerprint in enumerate(fingerprints):
        db_session.add(Fingerprint(
            track_id=track_id,
            hash=fingerprint,
            offset=i * 10  # Offset approximatif en secondes
        ))
    
    db_session.commit()
    return True
```

## 5. Métriques et évaluation

Pour évaluer l'efficacité des améliorations, nous recommandons de suivre ces métriques :

1. **Taux de détection locale** : Pourcentage de pistes identifiées localement sans recours aux services externes
2. **Précision** : Pourcentage de détections correctes parmi toutes les détections
3. **Temps de réponse** : Temps moyen nécessaire pour effectuer une détection locale
4. **Robustesse** : Taux de détection avec différentes qualités audio et différentes sections de pistes

## 6. Conclusion

L'amélioration de la détection locale avec empreintes digitales permettra de réduire significativement la dépendance aux services externes, d'améliorer les performances et de renforcer l'autonomie du système SODAV Monitor. Les recommandations présentées dans ce document offrent une feuille de route complète pour atteindre ces objectifs, avec des solutions concrètes et un plan d'implémentation progressif.

En mettant en œuvre ces améliorations, le système sera capable de reconnaître efficacement les pistes musicales même en l'absence de connexion Internet, tout en maintenant une haute précision et des performances optimales. 