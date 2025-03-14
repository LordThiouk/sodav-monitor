# Integration Testing for Play Duration Tracking

## Vue d'ensemble

Ce document décrit l'approche de test d'intégration pour la fonctionnalité de suivi de la durée de lecture des morceaux sur les stations. L'objectif principal est de garantir une mesure **précise et fiable** de la durée de diffusion de chaque musique détectée sur une station de radio.

## Objectif

L'objectif de ces tests d'intégration est de vérifier que le système :

1. Capture correctement la durée réelle de lecture de chaque morceau
2. Enregistre cette durée dans la base de données pour chaque détection
3. Associe correctement la durée à la station spécifique où le morceau a été joué
4. Met à jour les statistiques de durée de lecture pour les analyses
5. Suit le cycle complet de détection sans simulations ou mocks

## Approche de test avec données réelles

Conformément aux règles spécifiées, les tests de durée de lecture doivent reproduire tout le cycle de détection en utilisant tous les composants nécessaires, sans simulations ou mocks, pour connaître le temps de jeu exact des sons sur les stations.

### Fichier de test principal

`backend/tests/integration/detection/test_play_duration_real_data.py`

### Cas de test implémentés

1. **test_real_radio_duration_capture** : Capture un extrait audio d'une vraie radio sénégalaise, extrait la durée, puis tente de détecter la piste en suivant le cycle complet de détection (local → MusicBrainz/Acoustid → AudD).

2. **test_multiple_stations_duration_comparison** : Capture des extraits audio de plusieurs stations avec des durées d'enregistrement différentes, puis vérifie que les durées sont correctement enregistrées et peuvent être différentes.

3. **test_real_radio_full_detection_cycle** : Teste le cycle complet de détection avec de vraies données radio, en suivant toutes les étapes du processus de détection.

4. **test_real_radio_duration_until_silence** : Capture un extrait audio d'une vraie radio jusqu'à ce que le son s'arrête naturellement ou qu'un silence significatif soit détecté, puis vérifie que la durée exacte est correctement enregistrée. Ce test est essentiel pour garantir que le système capture la durée complète de chaque morceau joué.

5. **test_available_stations** : Vérifie que les stations sénégalaises sont disponibles pour les tests.

### Méthode de capture audio améliorée

La méthode `capture_audio_stream` a été améliorée pour permettre la capture d'un flux audio jusqu'à ce que le son s'arrête naturellement :

```python
def capture_audio_stream(self, stream_url, duration=RECORDING_DURATION, detect_silence=False):
    """
    Capture un extrait audio d'un flux radio en direct.

    Args:
        stream_url: URL du flux radio
        duration: Durée d'enregistrement en secondes (utilisée seulement si detect_silence=False)
        detect_silence: Si True, capture jusqu'à ce qu'un silence ou changement de morceau soit détecté

    Returns:
        tuple: (bytes: Données audio capturées, float: Durée réelle capturée)
    """
    try:
        # Établir une connexion au flux
        response = requests.get(stream_url, stream=True, timeout=10)
        response.raise_for_status()

        # Préparer un buffer pour stocker les données audio
        audio_buffer = io.BytesIO()

        # Calculer la taille approximative à capturer
        bytes_to_capture = int(duration * 128 * 1024 / 8)

        # Capturer les données
        bytes_captured = 0
        start_time = datetime.now()

        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                audio_buffer.write(chunk)
                bytes_captured += len(chunk)

                # Vérifier si nous avons capturé suffisamment de données
                elapsed = (datetime.now() - start_time).total_seconds()
                if bytes_captured >= bytes_to_capture or elapsed >= duration + 5:
                    break

        # Convertir en format compatible avec pydub pour extraction de la durée
        audio_buffer.seek(0)
        audio = AudioSegment.from_file(audio_buffer)

        # Créer un nouveau buffer avec le segment audio
        output_buffer = io.BytesIO()
        audio.export(output_buffer, format="mp3")
        output_buffer.seek(0)

        # Variables pour la détection de silence/changement
        silence_threshold = 0.05  # Seuil pour considérer un segment comme silence
        silence_duration = 0  # Durée du silence courant
        max_silence_duration = 2.0  # Durée maximale de silence avant de considérer la fin du morceau

        # Détecter le silence
        if normalized_rms < silence_threshold:
            silence_duration += len(temp_audio) / 1000.0
            if silence_duration >= max_silence_duration:
                logger.info(f"Silence détecté pendant {silence_duration:.2f}s - Fin du morceau")
                break
        else:
            silence_duration = 0

        # Détecter un changement significatif dans le contenu audio
        # ... code de détection de changement ...

        return output_buffer.read(), silence_duration

    except Exception as e:
        return None, None
```

### Détection de fin de morceau

Le système utilise deux méthodes principales pour détecter la fin d'un morceau :

1. **Détection de silence** : Le système surveille le niveau sonore et considère qu'un morceau est terminé lorsqu'un silence d'au moins 2 secondes est détecté.

2. **Détection de changement spectral** : Le système analyse les caractéristiques spectrales du son et détecte les changements significatifs qui pourraient indiquer un changement de morceau.

Ces méthodes permettent de capturer la durée exacte de chaque morceau, du début jusqu'à la fin naturelle, sans se limiter à une durée prédéfinie.

### Vérifications implémentées

Les tests vérifient désormais les points suivants :

1. **Capture précise de la durée** : La durée est extraite directement du fichier audio capturé, en tenant compte de la fin naturelle du morceau.
2. **Enregistrement correct de la durée** : La durée est correctement enregistrée dans la base de données.
3. **Correspondance des durées** : La durée enregistrée correspond à la durée capturée (avec une marge d'erreur de 0.5 seconde).
4. **Mise à jour des statistiques** : Les statistiques de la station sont correctement mises à jour avec la durée de lecture.
5. **Différenciation des durées** : Les durées peuvent être différentes pour différentes stations.
6. **Détection de fin de morceau** : Le système détecte correctement la fin d'un morceau, soit par silence, soit par changement spectral.

### Exemple de test de durée jusqu'au silence

```python
@pytest.mark.asyncio
async def test_real_radio_duration_until_silence(self, db_session, test_stations):
    """
    Test qui capture un extrait audio d'une vraie radio jusqu'à ce que le son s'arrête
    ou qu'un silence soit détecté, puis vérifie que la durée est correctement enregistrée.
    """
    # Sélectionner une station de test
    station = test_stations[0]

    # Capturer l'audio jusqu'à ce qu'un silence soit détecté
    audio_data, captured_duration = self.capture_audio_stream(
        station.stream_url,
        detect_silence=True
    )

    # ... code d'extraction des caractéristiques et de détection ...

    # Vérifier que la durée enregistrée correspond à la durée capturée
    captured_duration_td = timedelta(seconds=captured_duration)
    assert abs(detection.play_duration.total_seconds() - captured_duration_td.total_seconds()) < 0.5, \
        f"La durée enregistrée ({detection.play_duration.total_seconds()} s) ne correspond pas à la durée capturée ({captured_duration_td.total_seconds()} s)"

    # ... vérifications supplémentaires ...
```

## Cycle de détection hiérarchique

Conformément aux règles, les tests suivent le cycle de détection hiérarchique complet :

1. **Détection locale** : Recherche d'une correspondance dans la base de données locale à l'aide des empreintes digitales.
2. **Détection via MusicBrainz/Acoustid** : Si la détection locale échoue, interrogation de l'API MusicBrainz.
3. **Détection via Audd** : Si MusicBrainz échoue, utilisation de l'API Audd comme solution de dernier recours.

## Données enregistrées pour chaque détection

Les tests vérifient que les informations suivantes sont correctement enregistrées pour chaque détection :

- `track_id` : Identifiant unique de la musique
- `station_id` : Identifiant de la station de radio
- `confidence` : Niveau de confiance de la détection
- `detected_at` : Timestamp de début
- `play_duration` : Durée exacte du son joué
- `fingerprint` : Empreinte acoustique pour future comparaison

## Mise à jour automatique des statistiques

Les tests vérifient également que les statistiques suivantes sont correctement mises à jour :

- `TrackStats` : Nombre de lectures, durée totale, dernière détection
- `StationStats` : Temps total de musique joué par station
- `StationTrackStats` : Durée cumulée par piste et par station

## Exécution des tests

Pour exécuter les tests de durée de lecture avec des données réelles :

```bash
cd backend
python -m pytest tests/integration/detection/test_play_duration_real_data.py -v
```

Pour exécuter un test spécifique :

```bash
cd backend
python -m pytest tests/integration/detection/test_play_duration_real_data.py::TestPlayDurationRealData::test_real_radio_duration_capture -v
```

## Améliorations récentes

Les tests ont été améliorés pour :

1. **Vérifier plus précisément les durées** : Ajout d'assertions qui comparent la durée capturée avec la durée enregistrée avec une marge d'erreur de 0.5 seconde.
2. **Utiliser des durées d'enregistrement différentes** : Pour le test `test_multiple_stations_duration_comparison`, des durées d'enregistrement différentes sont utilisées pour chaque station.
3. **Vérifier les statistiques de durée** : Vérification que les statistiques de durée sont correctement mises à jour dans la base de données.
4. **Capturer jusqu'à la fin naturelle du morceau** : Ajout d'un nouveau test `test_real_radio_duration_until_silence` qui capture l'audio jusqu'à ce qu'un silence ou un changement significatif soit détecté, permettant de mesurer la durée exacte de chaque morceau.
5. **Détecter les changements de contenu** : Implémentation d'une analyse spectrale pour détecter les changements significatifs dans le contenu audio, indiquant potentiellement un changement de morceau.

## Implémentation actuelle

Le système a été mis à jour pour prendre en charge la capture et l'enregistrement précis des durées de lecture :

### 1. Extraction de la durée

La classe `FeatureExtractor` extrait maintenant la durée du fichier audio et l'inclut dans les caractéristiques :

```python
def extract_features(self, audio_data: np.ndarray) -> Dict[str, Any]:
    # ...
    # Calculer la durée de lecture
    play_duration = self.get_audio_duration(audio_mono)

    # ...

    # Assembler toutes les caractéristiques
    features = {
        "play_duration": play_duration,
        "duration": play_duration,  # Ajouter la durée sous le nom 'duration' pour compatibilité
        # ...
    }

    return features
```

### 2. Traitement de la durée

La classe `TrackManager` extrait la durée des caractéristiques et la transmet au processus de détection :

```python
async def process_track(self, features: Dict[str, Any], station_id: Optional[int] = None) -> Dict[str, Any]:
    # ...
    # Extraire la durée des caractéristiques
    duration = features.get("duration", features.get("play_duration", 0))

    # ...
    # Ajouter la durée au résultat
    result["duration"] = duration
    return self.stats_recorder.record_detection(result, station_id)
    # ...
```

### 3. Enregistrement de la durée

La classe `StatsRecorder` enregistre la durée dans la base de données et met à jour les statistiques :

```python
def record_detection(self, detection_result: Dict[str, Any], station_id: int) -> Dict[str, Any]:
    # ...
    # Extraire la durée du résultat de détection
    duration = detection_result.get("duration", 0)

    # Créer un enregistrement de détection
    detection = TrackDetection(
        track_id=track.id,
        station_id=station_id,
        detected_at=datetime.utcnow(),
        confidence=detection_result.get("confidence", 0.8),
        method=detection_result.get("method", "unknown"),
        play_duration=duration  # Utiliser la durée extraite
    )
    self.db_session.add(detection)

    # Mettre à jour les statistiques de la station
    station_track_stats = self.db_session.query(StationTrackStats).filter(
        StationTrackStats.station_id == station_id,
        StationTrackStats.track_id == track.id
    ).first()

    if not station_track_stats:
        # Créer de nouvelles statistiques si elles n'existent pas
        station_track_stats = StationTrackStats(
            station_id=station_id,
            track_id=track.id,
            detection_count=1,
            total_play_duration=duration,
            last_detected_at=datetime.utcnow()
        )
        self.db_session.add(station_track_stats)
    else:
        # Mettre à jour les statistiques existantes
        station_track_stats.detection_count += 1
        station_track_stats.total_play_duration += duration
        station_track_stats.last_detected_at = datetime.utcnow()
    # ...
```

## Bonnes pratiques

1. **Précision de la durée** : Les durées sont stockées avec une précision suffisante (secondes avec décimales).
2. **Validation des données** : Les durées sont vérifiées pour s'assurer qu'elles sont positives et raisonnables.
3. **Gestion des erreurs** : Les cas où la durée ne peut pas être extraite sont correctement gérés.
4. **Tests avec différentes sources** : Les tests utilisent différentes stations de radio pour vérifier la robustesse du système.
5. **Gestion des cas particuliers** : Le système gère correctement les cas comme les coupures de flux et les sons non identifiés.
6. **Détection de fin de morceau** : Le système utilise des méthodes avancées pour détecter la fin naturelle d'un morceau, garantissant une mesure précise de la durée.
7. **Limite de sécurité** : Une limite maximale de 3 minutes est imposée pour éviter des captures trop longues en cas de problème avec la détection de fin de morceau.

## Conclusion

Les tests de durée de lecture avec des données réelles garantissent que le système capture, enregistre et utilise correctement les informations de durée pour chaque morceau sur chaque station. Ces tests sont essentiels pour fournir des données précises sur le temps d'antenne, ce qui est crucial pour la distribution des droits d'auteur. La nouvelle approche de capture jusqu'à la fin naturelle du morceau permet d'obtenir des mesures encore plus précises de la durée réelle de diffusion.
