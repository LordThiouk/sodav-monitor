# Recommandations Techniques pour le Système de Détection

Ce document présente des recommandations techniques détaillées pour améliorer le système de détection musicale du projet SODAV Monitor, en mettant l'accent sur la robustesse, les performances et la qualité des données.

## 1. Améliorations du code

### 1.1. Refactorisation du processus de détection

**Problème** : Le processus de détection est actuellement réparti entre plusieurs méthodes et classes, ce qui rend difficile le suivi du cycle de vie complet d'une détection.

**Recommandations** :
- Créer une classe `DetectionProcess` qui encapsule tout le cycle de vie d'une détection.
- Implémenter un pattern d'état (State Pattern) pour représenter les différentes étapes du processus de détection.
- Centraliser la logique d'extraction des métadonnées dans une classe dédiée.

**Exemple de code** :
```python
class DetectionProcess:
    def __init__(self, audio_data, station_id, track_manager):
        self.audio_data = audio_data
        self.station_id = station_id
        self.track_manager = track_manager
        self.state = InitialState(self)
        
    def process(self):
        return self.state.process()
        
    def transition_to(self, state):
        self.state = state
        
class DetectionState(ABC):
    @abstractmethod
    def process(self):
        pass
        
class LocalDetectionState(DetectionState):
    def process(self):
        # Logique de détection locale
        # Si succès, transition vers FinalizeDetectionState
        # Si échec, transition vers AcoustIDDetectionState
        pass
```

### 1.2. Amélioration de la gestion des erreurs

**Problème** : La gestion des erreurs est inconsistante à travers le code, ce qui peut entraîner des détections incomplètes ou des données manquantes.

**Recommandations** :
- Implémenter un système de gestion d'erreurs centralisé avec des types d'erreurs spécifiques.
- Utiliser des décorateurs pour la gestion des erreurs communes.
- Ajouter des mécanismes de récupération automatique pour les erreurs non critiques.

**Exemple de code** :
```python
class DetectionError(Exception):
    """Base class for detection errors."""
    pass
    
class APIError(DetectionError):
    """Error when calling external APIs."""
    pass
    
def with_error_handling(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except APIError as e:
            logger.error(f"API Error in {func.__name__}: {e}")
            # Implement recovery logic
        except DetectionError as e:
            logger.error(f"Detection Error in {func.__name__}: {e}")
            # Implement fallback
        except Exception as e:
            logger.critical(f"Unexpected error in {func.__name__}: {e}")
            # Log and re-raise
            raise
    return wrapper
```

### 1.3. Optimisation des requêtes à la base de données

**Problème** : Les requêtes à la base de données sont parfois inefficaces, avec des requêtes multiples là où une seule suffirait.

**Recommandations** :
- Utiliser des jointures pour récupérer les données liées en une seule requête.
- Implémenter des requêtes en masse pour les mises à jour multiples.
- Utiliser des index appropriés pour les champs fréquemment recherchés (ISRC, fingerprint).

**Exemple de code** :
```python
# Avant
track = db_session.query(Track).filter_by(id=track_id).first()
artist = db_session.query(Artist).filter_by(id=track.artist_id).first()

# Après
track_with_artist = db_session.query(Track, Artist).join(Artist).filter(Track.id == track_id).first()
```

## 2. Améliorations de l'architecture

### 2.1. Mise en place d'un système de cache

**Problème** : Les appels répétés aux API externes sont coûteux en temps et en ressources.

**Recommandations** :
- Implémenter un cache Redis pour les résultats de détection récents.
- Mettre en cache les empreintes digitales fréquemment utilisées.
- Utiliser un TTL (Time To Live) approprié pour les données en cache.

**Exemple de configuration** :
```python
CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0',
    'CACHE_DEFAULT_TIMEOUT': 86400  # 24 heures
}

@cached(timeout=3600, key_prefix='audd_detection')
async def detect_track_with_audd(audio_data):
    # Logique de détection avec AudD
    pass
```

### 2.2. Implémentation d'un système de file d'attente

**Problème** : Le traitement synchrone des détections peut entraîner des blocages et des timeouts.

**Recommandations** :
- Utiliser Celery ou RQ pour mettre en file d'attente les tâches de détection.
- Implémenter un système de priorité pour les détections.
- Ajouter des workers dédiés pour les différentes étapes du processus de détection.

**Exemple de configuration** :
```python
# Configuration Celery
app = Celery('sodav_monitor', broker='redis://localhost:6379/1')

@app.task(bind=True, max_retries=3)
def detect_track_task(self, audio_data, station_id):
    try:
        return detect_track(audio_data, station_id)
    except Exception as e:
        self.retry(exc=e, countdown=60)  # Retry after 60 seconds
```

### 2.3. Mise en place d'un système de monitoring

**Problème** : Il est difficile de suivre les performances et les erreurs du système de détection en temps réel.

**Recommandations** :
- Implémenter Prometheus pour la collecte de métriques.
- Utiliser Grafana pour la visualisation des métriques.
- Mettre en place des alertes pour les situations critiques.

**Exemple de métriques à suivre** :
- Taux de détection réussie par station
- Temps de réponse des API externes
- Nombre de détections par minute
- Utilisation des ressources (CPU, mémoire, réseau)
- Taux d'erreur par type d'erreur

## 3. Améliorations de la qualité des données

### 3.1. Validation des métadonnées

**Problème** : Les métadonnées reçues des API externes ne sont pas toujours validées avant d'être sauvegardées.

**Recommandations** :
- Implémenter des schémas de validation avec Pydantic.
- Ajouter des règles de validation spécifiques pour les ISRC et autres identifiants.
- Mettre en place un système de correction automatique pour les erreurs courantes.

**Exemple de code** :
```python
from pydantic import BaseModel, validator

class TrackMetadata(BaseModel):
    title: str
    artist: str
    isrc: Optional[str] = None
    
    @validator('isrc')
    def validate_isrc(cls, v):
        if v is None:
            return v
        if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}[0-9]{7}$', v):
            raise ValueError(f'Invalid ISRC format: {v}')
        return v
```

### 3.2. Déduplication des pistes

**Problème** : Des pistes en double peuvent être créées dans la base de données malgré des métadonnées similaires.

**Recommandations** :
- Utiliser l'ISRC comme identifiant principal pour la déduplication.
- Implémenter des algorithmes de correspondance floue pour les titres et les noms d'artistes.
- Mettre en place un processus de fusion pour les pistes en double détectées.

**Exemple de code** :
```python
def find_duplicate_tracks(title, artist, isrc=None):
    if isrc:
        # Recherche par ISRC d'abord
        track = db_session.query(Track).filter_by(isrc=isrc).first()
        if track:
            return track
    
    # Recherche par titre et artiste avec correspondance floue
    candidates = db_session.query(Track).join(Artist).filter(
        func.similarity(Track.title, title) > 0.8,
        func.similarity(Artist.name, artist) > 0.8
    ).all()
    
    # Logique de sélection du meilleur candidat
    return best_candidate(candidates, title, artist)
```

### 3.3. Enrichissement des métadonnées

**Problème** : Les métadonnées sont parfois incomplètes, même après la détection.

**Recommandations** :
- Intégrer des sources de métadonnées supplémentaires (MusicBrainz, Discogs).
- Mettre en place un processus d'enrichissement périodique pour les pistes existantes.
- Ajouter des métadonnées supplémentaires (genre, BPM, année, etc.).

**Exemple de code** :
```python
async def enrich_track_metadata(track_id):
    track = db_session.query(Track).filter_by(id=track_id).first()
    if not track:
        return False
    
    # Enrichir avec MusicBrainz
    if track.isrc:
        mb_data = await musicbrainz_service.get_recording_by_isrc(track.isrc)
        if mb_data:
            update_track_with_musicbrainz_data(track, mb_data)
    
    # Enrichir avec Discogs
    discogs_data = await discogs_service.search_release(track.title, track.artist.name)
    if discogs_data:
        update_track_with_discogs_data(track, discogs_data)
    
    db_session.commit()
    return True
```

### 3.4. Utilisation efficace de la contrainte d'unicité ISRC

**Problème** : Malgré l'implémentation de la contrainte d'unicité ISRC, le système ne l'utilise pas toujours de manière optimale dans le processus de détection.

**Recommandations** :
- Prioriser la recherche par ISRC dans toutes les méthodes de détection.
- Standardiser le format de retour des méthodes de détection pour inclure les informations ISRC.
- Implémenter une vérification systématique de l'ISRC avant toute création de piste.
- Attribuer un niveau de confiance maximal (1.0) aux correspondances par ISRC.
- Mettre à jour les statistiques de lecture pour les pistes existantes au lieu de créer des doublons.

**Exemple de code amélioré pour la détection** :
```python
async def find_track_by_metadata(self, metadata, station_id=None):
    """Recherche une piste par ses métadonnées, en priorisant l'ISRC."""
    # Vérifier d'abord par ISRC si disponible
    if metadata.get('isrc'):
        existing_track = self.db_session.query(Track).filter(
            Track.isrc == metadata['isrc']
        ).first()
        
        if existing_track:
            self.logger.info(f"Found existing track with ISRC {metadata['isrc']}: {existing_track.title}")
            
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

**Avantages de cette approche** :
1. **Intégrité des données** : Garantit qu'un même enregistrement musical n'est représenté qu'une seule fois dans la base de données.
2. **Statistiques précises** : Toutes les détections d'une même piste sont consolidées, ce qui permet d'obtenir des statistiques de lecture précises.
3. **Performances améliorées** : La recherche par ISRC est rapide grâce à l'index, ce qui améliore les performances du système.
4. **Réduction des faux positifs** : L'ISRC étant un identifiant standard de l'industrie, son utilisation réduit les risques d'erreurs d'identification.
5. **Rapports plus précis** : Les rapports générés reflètent correctement le nombre réel de diffusions par piste.

**Implémentation technique** :
- Vérifier que toutes les méthodes de détection (`find_acoustid_match`, `find_audd_match`, etc.) vérifient d'abord l'existence d'une piste avec le même ISRC.
- Standardiser le format de retour de ces méthodes pour inclure les informations complètes de la piste et un niveau de confiance approprié.
- Ajouter des tests spécifiques pour valider le bon fonctionnement de la contrainte d'unicité ISRC.
- Mettre en place un système de monitoring pour suivre l'utilisation de l'ISRC dans le processus de détection.

**Exemple de test pour valider la contrainte d'unicité ISRC** :
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

## 4. Améliorations des tests

### 4.1. Tests unitaires complets

**Problème** : La couverture des tests est insuffisante, en particulier pour les scénarios d'erreur.

**Recommandations** :
- Atteindre une couverture de tests d'au moins 90% pour le code de détection.
- Ajouter des tests pour tous les scénarios d'erreur possibles.
- Utiliser des mocks pour simuler les API externes.

**Exemple de code** :
```python
@pytest.mark.asyncio
async def test_audd_service_isrc_extraction():
    # Préparer les données de test
    mock_response = {
        "status": "success",
        "result": {
            "artist": "Test Artist",
            "title": "Test Track",
            "album": "Test Album",
            "release_date": "2023-01-01",
            "label": "Test Label",
            "apple_music": {"isrc": "ABCDE1234567"}
        }
    }
    
    # Mocker la réponse de l'API
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json.return_value = mock_response
        
        # Appeler le service
        audd_service = AuddService("test_api_key")
        result = await audd_service.detect_track(b"test_audio_data")
        
        # Vérifier le résultat
        assert result["success"] is True
        assert result["detection"]["isrc"] == "ABCDE1234567"
```

### 4.2. Tests d'intégration

**Problème** : Les interactions entre les différents composants ne sont pas suffisamment testées.

**Recommandations** :
- Ajouter des tests d'intégration pour le cycle complet de détection.
- Utiliser des conteneurs Docker pour les dépendances externes (PostgreSQL, Redis).
- Mettre en place des tests de bout en bout avec des échantillons audio réels.

**Exemple de configuration** :
```python
@pytest.fixture(scope="session")
def postgres_container():
    container = PostgresContainer("postgres:13")
    container.start()
    yield container
    container.stop()

@pytest.fixture
def db_session(postgres_container):
    engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.mark.integration
def test_complete_detection_cycle(db_session):
    # Test du cycle complet avec une base de données réelle
    pass
```

### 4.3. Tests de performance

**Problème** : Les performances du système de détection ne sont pas régulièrement évaluées.

**Recommandations** :
- Mettre en place des tests de charge pour simuler un grand nombre de détections simultanées.
- Mesurer les temps de réponse pour chaque étape du processus de détection.
- Établir des seuils de performance acceptables et alerter en cas de dégradation.

**Exemple de code** :
```python
@pytest.mark.performance
async def test_detection_performance():
    # Préparer les données de test
    audio_samples = load_test_samples(100)  # 100 échantillons audio
    
    # Mesurer le temps de détection
    start_time = time.time()
    results = await asyncio.gather(*[
        detect_track(sample, station_id=1)
        for sample in audio_samples
    ])
    end_time = time.time()
    
    # Analyser les résultats
    total_time = end_time - start_time
    success_rate = sum(1 for r in results if r["success"]) / len(results)
    avg_time_per_detection = total_time / len(results)
    
    # Vérifier les seuils de performance
    assert avg_time_per_detection < 2.0  # Max 2 secondes par détection
    assert success_rate > 0.9  # Au moins 90% de réussite
```

## 5. Améliorations de la documentation

### 5.1. Documentation du code

**Problème** : La documentation du code est parfois insuffisante ou obsolète.

**Recommandations** :
- Ajouter des docstrings complets pour toutes les classes et méthodes.
- Utiliser Sphinx pour générer une documentation automatique.
- Maintenir des exemples d'utilisation à jour.

**Exemple de docstring** :
```python
async def detect_track(audio_data: bytes, station_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Détecte une piste musicale à partir de données audio.
    
    Cette méthode utilise l'API AudD pour identifier une piste musicale à partir
    d'un échantillon audio. Elle extrait également les métadonnées, y compris l'ISRC,
    à partir des résultats de détection.
    
    Args:
        audio_data: Données audio brutes en bytes.
        station_id: ID optionnel de la station radio.
        
    Returns:
        Un dictionnaire contenant:
        - success (bool): Indique si la détection a réussi.
        - detection (dict): Métadonnées de la piste détectée (si success=True).
        - error (str): Message d'erreur (si success=False).
        
    Raises:
        APIError: Si l'appel à l'API AudD échoue.
        
    Examples:
        >>> audio_data = open("sample.mp3", "rb").read()
        >>> result = await detect_track(audio_data)
        >>> if result["success"]:
        ...     print(f"Track: {result['detection']['title']} by {result['detection']['artist']}")
        ...     print(f"ISRC: {result['detection'].get('isrc')}")
    """
```

### 5.2. Documentation de l'architecture

**Problème** : L'architecture globale du système n'est pas suffisamment documentée.

**Recommandations** :
- Créer des diagrammes d'architecture (C4 model).
- Documenter les flux de données entre les composants.
- Maintenir un glossaire des termes techniques.

**Exemple de documentation** :
```markdown
# Architecture du Système de Détection

## Composants Principaux

1. **StationMonitor** : Capture les échantillons audio des stations radio.
2. **AudioAnalyzer** : Analyse les échantillons audio pour déterminer leur type.
3. **TrackManager** : Gère la détection, la création et la mise à jour des pistes.
4. **ExternalServiceHandler** : Coordonne les appels aux services externes.

## Flux de Données

1. StationMonitor capture un échantillon audio.
2. AudioAnalyzer détermine si l'échantillon contient de la musique.
3. TrackManager tente de trouver une correspondance locale.
4. Si aucune correspondance n'est trouvée, ExternalServiceHandler appelle AcoustID puis AudD.
5. TrackManager crée ou met à jour la piste dans la base de données.
6. TrackManager enregistre la détection et met à jour les statistiques.

## Diagramme de Séquence

[Insérer diagramme de séquence]
```

### 5.3. Documentation des API

**Problème** : Les API internes et externes ne sont pas suffisamment documentées.

**Recommandations** :
- Utiliser OpenAPI/Swagger pour documenter les API REST.
- Documenter les formats de données attendus et retournés.
- Maintenir des exemples de requêtes et de réponses.

**Exemple de documentation OpenAPI** :
```yaml
paths:
  /api/detect:
    post:
      summary: Détecte une piste musicale à partir d'un échantillon audio
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                audio:
                  type: string
                  format: binary
                station_id:
                  type: integer
      responses:
        '200':
          description: Détection réussie
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  detection:
                    type: object
                    properties:
                      title:
                        type: string
                      artist:
                        type: string
                      isrc:
                        type: string
```

## 6. Plan d'implémentation

### 6.1. Priorités à court terme (1-2 mois)

1. **Correction des bugs critiques** :
   - Finaliser la correction de la sauvegarde des ISRC.
   - Corriger les problèmes de finalisation des détections.

2. **Amélioration des tests** :
   - Augmenter la couverture des tests unitaires.
   - Ajouter des tests d'intégration pour le cycle complet de détection.

3. **Documentation** :
   - Documenter le cycle de vie d'une détection.
   - Ajouter des docstrings pour les méthodes principales.

### 6.2. Priorités à moyen terme (3-6 mois)

1. **Refactorisation du code** :
   - Implémenter la classe `DetectionProcess`.
   - Améliorer la gestion des erreurs.

2. **Optimisation des performances** :
   - Mettre en place un système de cache.
   - Optimiser les requêtes à la base de données.

3. **Amélioration de la qualité des données** :
   - Implémenter la validation des métadonnées.
   - Mettre en place un système de déduplication.

### 6.3. Priorités à long terme (6-12 mois)

1. **Architecture avancée** :
   - Implémenter un système de file d'attente.
   - Mettre en place un système de monitoring complet.

2. **Enrichissement des données** :
   - Intégrer des sources de métadonnées supplémentaires.
   - Mettre en place un processus d'enrichissement périodique.

3. **Automatisation** :
   - Automatiser les tests de performance.
   - Mettre en place un pipeline CI/CD complet.

## 7. Conclusion

L'amélioration du système de détection musicale est un processus continu qui nécessite des efforts dans plusieurs domaines : code, architecture, qualité des données, tests et documentation. En suivant les recommandations de ce document, le système SODAV Monitor pourra atteindre un niveau supérieur de robustesse, de performance et de qualité des données, garantissant ainsi une gestion précise des droits d'auteur et la génération de rapports fiables. 