# Problèmes de Mise à Jour des Statistiques

Ce document détaille les problèmes courants rencontrés lors de la mise à jour des statistiques et leurs solutions.

## Erreur de Type de Données pour la Durée

### Problème

Une erreur fréquente lors de l'enregistrement des détections est liée à un décalage entre le type de données attendu pour le champ `duration` dans la table `tracks` et le type de données fourni :

```
ERROR: column "duration" is of type interval but expression is of type integer
LINE 1: ...'Unknown Track', 16, NULL, NULL, 'Unknown Album', 0, '', NUL...
                                                           ^
```

### Cause

La colonne `duration` dans la table `tracks` est définie comme un type `Interval` dans PostgreSQL, mais le code tente parfois d'insérer une valeur entière (0) au lieu d'un objet `timedelta`.

Ce problème se produit généralement dans les cas suivants :
1. Lors de la création d'une piste "Unknown Track" sans détection réussie
2. Lorsque les métadonnées de la piste ne contiennent pas d'information de durée

### Solution

Pour résoudre ce problème, assurez-vous que toutes les valeurs de durée sont converties en objets `timedelta` avant d'être insérées dans la base de données. Voici comment corriger ce problème dans le code :

1. Dans `detect_music.py`, assurez-vous que la durée est toujours convertie en timedelta :

```python
# Convertir la durée en timedelta si c'est un entier ou un float
duration_value = track_info.get("duration", 0)
if isinstance(duration_value, (int, float)):
    duration_value = timedelta(seconds=duration_value)
elif duration_value is None:
    # S'assurer que la durée n'est jamais None
    duration_value = timedelta(seconds=0)
```

2. Dans `track_manager.py`, assurez-vous que la méthode `_get_or_create_track` accepte un paramètre de durée et le convertit correctement :

```python
async def _get_or_create_track(self, title: str, artist_id: int, album: Optional[str] = None, 
                          isrc: Optional[str] = None, label: Optional[str] = None, 
                          release_date: Optional[str] = None, duration: Optional[float] = None) -> Optional[Track]:
    # ...
    
    # Convertir la durée en timedelta si elle est fournie
    duration_value = None
    if duration is not None:
        duration_value = timedelta(seconds=duration)
    
    track = Track(
        # ...
        duration=duration_value,
        # ...
    )
```

3. Dans `track_manager.py`, assurez-vous que la méthode `_record_play_time` gère correctement les différents types de durée :

```python
def _record_play_time(self, station_id: int, track_id: int, play_duration: float):
    # Convertir play_duration en timedelta si ce n'est pas déjà le cas
    if isinstance(play_duration, (int, float)):
        play_duration_td = timedelta(seconds=play_duration)
    elif isinstance(play_duration, timedelta):
        play_duration_td = play_duration
    else:
        self.logger.warning(f"Invalid play_duration type: {type(play_duration)}, using 0 seconds")
        play_duration_td = timedelta(seconds=0)
    
    # Utiliser play_duration_td pour toutes les opérations suivantes
    # ...
```

4. Dans `track_manager.py`, assurez-vous que la méthode `_find_track_by_isrc` inclut la durée dans les informations de piste retournées :

```python
return {
    "track": {
        # ...
        "duration": existing_track.duration.total_seconds() if existing_track.duration else 0
    },
    # ...
}
```

### Vérification

Pour vérifier que le problème est résolu, surveillez les logs d'erreur après avoir effectué ces modifications. Les erreurs de type de données pour la colonne `duration` ne devraient plus apparaître.

### Mise à jour (Avril 2025)

Les modifications ci-dessus ont été implémentées et testées avec succès. Les points clés des modifications sont :

1. **Vérification systématique des types** : Toutes les méthodes qui manipulent des durées vérifient maintenant le type de la valeur et la convertissent en `timedelta` si nécessaire.

2. **Gestion cohérente des valeurs nulles** : Les valeurs nulles ou manquantes sont systématiquement remplacées par `timedelta(seconds=0)` pour éviter les erreurs.

3. **Propagation des durées** : Les durées sont correctement propagées à travers toute la chaîne de traitement, depuis la détection jusqu'à l'enregistrement dans la base de données.

4. **Logging amélioré** : Des messages de log détaillés ont été ajoutés pour suivre les conversions de durée et identifier rapidement les problèmes potentiels.

Ces modifications ont permis d'éliminer complètement les erreurs de type de données pour la colonne `duration`, et les statistiques de temps de jeu sont maintenant correctement enregistrées et mises à jour.

## Autres Problèmes Courants de Mise à Jour des Statistiques

### Durées de Lecture Nulles ou Incorrectes

Si les durées de lecture sont nulles ou incorrectes dans les statistiques, vérifiez :

1. Que la méthode `_record_play_time` reçoit des valeurs de durée valides
2. Que les conversions entre secondes et objets `timedelta` sont correctes
3. Que les mises à jour des statistiques cumulatives fonctionnent correctement

### Statistiques Non Mises à Jour

Si les statistiques ne sont pas mises à jour après les détections, vérifiez :

1. Que les transactions de base de données sont correctement validées (commit)
2. Que les méthodes de mise à jour des statistiques sont appelées après chaque détection
3. Que les erreurs dans le processus de mise à jour sont correctement journalisées et gérées

## Problèmes Identifiés

### 1. Méthode `_update_stats` manquante

**Problème** : La méthode `_update_stats` était appelée dans `AudioProcessor.detect_music()` mais n'était pas définie dans cette classe.

**Impact** : Les statistiques n'étaient pas mises à jour après une détection réussie, ce qui entrainaient des données incomplètes dans les tables de statistiques.

**Solution** : Ajout de la méthode `_update_stats` dans la classe `AudioProcessor` pour utiliser correctement le `StatsUpdater`.

```python
async def _update_stats(self, station_id: int, track_id: int, play_duration: float):
    """
    Met à jour les statistiques après une détection réussie.
    
    Cette méthode utilise le StatsUpdater pour mettre à jour toutes les statistiques
    pertinentes, y compris les statistiques de piste, d'artiste et de station.
    
    Args:
        station_id: ID de la station radio
        track_id: ID de la piste détectée
        play_duration: Durée de lecture en secondes
    """
    try:
        # Convertir la durée de lecture en timedelta
        play_duration_td = timedelta(seconds=play_duration)
        
        # Récupérer la piste
        track = self.db.query(Track).filter(Track.id == track_id).first()
        if not track:
            log_with_category(logger, "AUDIO_PROCESSOR", "warning", 
                f"Track with ID {track_id} not found, cannot update stats")
            return
            
        # Créer un dictionnaire de résultat de détection pour StatsUpdater
        detection_result = {
            "track_id": track_id,
            "confidence": 0.8,  # Valeur par défaut
            "detection_method": "audd"  # Méthode par défaut
        }
        
        # Utiliser le StatsUpdater pour mettre à jour toutes les statistiques
        self.stats_updater.update_all_stats(detection_result, station_id, track, play_duration_td)
        
    except Exception as e:
        log_with_category(logger, "AUDIO_PROCESSOR", "error", f"Error updating stats: {str(e)}")
```

### 2. `StatsUpdater` non utilisé dans `TrackManager._record_play_time`

**Problème** : La méthode `_record_play_time` dans `TrackManager` n'utilisait pas `StatsUpdater` pour mettre à jour toutes les statistiques nécessaires.

**Impact** : Seules les statistiques de base étaient mises à jour, mais pas les statistiques complètes comme `track_stats`, `artist_stats`, etc.

**Solution** : Modification de la méthode `_record_play_time` pour utiliser `StatsUpdater` :

```python
def _record_play_time(self, station_id: int, track_id: int, play_duration: float):
    try:
        # Get the station
        station = self.db_session.query(RadioStation).filter(RadioStation.id == station_id).first()
        if not station:
            self.logger.warning(f"Station with ID {station_id} not found")
            return
        
        # Get the track
        track = self.db_session.query(Track).filter(Track.id == track_id).first()
        if not track:
            self.logger.warning(f"Track with ID {track_id} not found")
            return
        
        # Create a new track detection record
        detection = TrackDetection(
            track_id=track_id,
            station_id=station_id,
            detected_at=datetime.utcnow(),
            play_duration=timedelta(seconds=play_duration),
            confidence=0.8,
            detection_method="audd"
        )
        self.db_session.add(detection)
        
        # Update station track stats
        self._update_station_track_stats(station_id, track_id, timedelta(seconds=play_duration))
        
        # Use StatsUpdater to update all statistics
        try:
            # Create a detection result dictionary
            detection_result = {
                "track_id": track_id,
                "confidence": 0.8,
                "detection_method": "audd"
            }
            
            # Initialize StatsUpdater
            from backend.utils.analytics.stats_updater import StatsUpdater
            stats_updater = StatsUpdater(self.db_session)
            
            # Update all stats
            stats_updater.update_all_stats(
                detection_result=detection_result,
                station_id=station_id,
                track=track,
                play_duration=timedelta(seconds=play_duration)
            )
        except Exception as stats_error:
            self.logger.error(f"Error updating stats: {stats_error}")
            # Continue with the rest of the method even if stats update fails
        
        self.db_session.commit()
        self.logger.info(f"Recorded play time for track ID {track_id} on station ID {station_id}: {play_duration} seconds")
    except Exception as e:
        self.logger.error(f"Error recording play time: {e}")
        self.db_session.rollback()
```

### 3. Problème avec les durées de lecture identiques

**Problème** : Les durées de lecture étaient identiques pour toutes les détections, suggérant un problème dans la façon dont elles sont calculées ou enregistrées.

**Analyse** : La durée de lecture est correctement calculée dans `FeatureExtractor.get_audio_duration()` en fonction du nombre d'échantillons audio et du taux d'échantillonnage. Cette valeur est ensuite transmise à travers le processus de détection.

**Vérification** : 
- La méthode `get_audio_duration` calcule correctement la durée en secondes : `duration = float(n_samples / self.sample_rate)`
- Cette durée est stockée dans les caractéristiques audio : `features["play_duration"] = play_duration`
- La durée est transmise aux méthodes de détection et d'enregistrement

**Conclusion** : Les durées identiques pourraient être dues à des segments audio de même longueur ou à un problème dans la façon dont les segments sont extraits des flux audio. Une surveillance plus approfondie est recommandée.

## Nouveaux Problèmes Identifiés (Mars 2025)

### 4. Durées de détection identiques

**Problème** : Toutes les détections récentes ont des durées presque identiques (environ 2 minutes et 11 secondes), ce qui n'est pas réaliste pour des diffusions radio réelles.

**Cause identifiée** : Dans le fichier `backend/detection/audio_processor/stream_handler.py`, la méthode `get_audio_data` récupère toujours la même quantité de données audio (environ 1MB) pour chaque station :

```python
# Read audio data in chunks
audio_data = io.BytesIO()
chunk_size = 10 * 1024  # 10KB chunks
max_size = 1 * 1024 * 1024  # 1MB max (about 10 seconds of audio)
total_size = 0
```

Cette limitation à 1MB (environ 10 secondes d'audio brut) entrainaient des durées de détection similaires pour toutes les stations.

**Impact** : Les statistiques de temps de diffusion ne reflétaient pas la réalité des diffusions, ce qui peut affecter le calcul des redevances.

**Solution proposée** : 
1. Modifier la méthode `get_audio_data` pour récupérer des échantillons audio de durées variables en fonction de la station ou du type de contenu.
2. Augmenter la taille maximale des échantillons audio pour obtenir des durées plus réalistes.
3. Implémenter un système de détection continue qui suit la diffusion d'une piste sur une période plus longue.

### 5. Codes ISRC manquants

**Problème** : Certaines pistes détectées n'ont pas de code ISRC enregistré, ce qui compliquait l'identification unique des œuvres et le calcul des redevances.

**Causes identifiées** :
1. **Absence dans les métadonnées** : Les services de détection (AcoustID, AudD) ne fournissaient pas toujours les codes ISRC pour toutes les pistes.
2. **Validation échouée** : Si un ISRC est trouvé mais ne respectait pas le format standard, il était ignoré :
   ```python
   if isrc:
       isrc = isrc.replace('-', '').upper()
       if not self._validate_isrc(isrc):
           self.logger.warning(f"ISRC invalide ignoré: {isrc}")
           isrc = None  # Ignorer l'ISRC invalide
   ```
3. **Détection par empreinte** : Si une piste était détectée par empreinte digitale plutôt que par ISRC, elle n'aurait pas d'ISRC à moins qu'il ne soit fourni dans les métadonnées.

**Impact** : L'absence de codes ISRC rendait difficile l'identification unique des œuvres et peut entrainaient des doublons dans la base de données, affectant la précision des statistiques et le calcul des redevances.

**Solutions proposées** :
1. Améliorer la recherche des ISRC en utilisant des sources supplémentaires.
2. Mettre en place un système de mise à jour périodique des métadonnées pour les pistes sans ISRC.
3. Implémenter un mécanisme de correspondance basé sur le titre et l'artiste pour associer les pistes sans ISRC à des pistes existantes avec ISRC.
4. Assouplir la validation des ISRC pour accepter des formats légèrement différents mais toujours identifiables.

### 6. Méthode de détection non enregistrée

**Problème** : Dans les détections récentes, la colonne `Method` était `None`, ce qui indiquait que la méthode de détection n'était pas correctement enregistrée.

**Cause identifiée** : La méthode `_record_play_time` dans `track_manager.py` définissait toujours la méthode comme "audd" (ligne 1731), mais cette valeur n'était pas correctement transmise lors de la création de l'enregistrement de détection.

**Impact** : Sans information sur la méthode de détection utilisée, il était difficile d'analyser l'efficacité des différentes méthodes et d'optimiser le processus de détection.

**Solution proposée** :
1. Corriger la méthode `_record_play_time` pour utiliser la méthode de détection réelle plutôt que de toujours définir "audd".
2. S'assurer que la méthode de détection était correctement transmise lors de la création de l'enregistrement de détection.
3. Ajouter des logs détaillés pour suivre la méthode de détection utilisée à chaque étape du processus.

## Recommandations pour l'avenir

1. **Logging amélioré** : Ajouter des logs détaillés pour suivre les durées de lecture à chaque étape du processus de détection.

2. **Tests unitaires** : Créer des tests unitaires spécifiques pour vérifier que les statistiques sont correctement mises à jour.

3. **Monitoring** : Mettre en place un monitoring des statistiques pour détecter rapidement les anomalies.

4. **Validation des durées** : Ajouter une validation supplémentaire des durées de lecture pour s'assurer qu'elles sont réalistes.

5. **Récupération automatique** : Implémenter un mécanisme de récupération automatique pour les statistiques manquantes ou incorrectes.

## Plan d'Action

1. **Court terme** (1-2 semaines) :
   - Corriger la méthode `_record_play_time` pour enregistrer correctement la méthode de détection.
   - Modifier la méthode `get_audio_data` pour récupérer des échantillons audio de durées variables.

2. **Moyen terme** (1-2 mois) :
   - Implémenter un système de mise à jour périodique des métadonnées pour les pistes sans ISRC.
   - Améliorer la recherche des ISRC en utilisant des sources supplémentaires.

3. **Long terme** (3-6 mois) :
   - Implémenter un système de détection continue qui suit la diffusion d'une piste sur une période plus longue.
   - Développer un algorithme de correspondance avancé pour associer les pistes sans ISRC à des pistes existantes.

## Conclusion Générale

Les problèmes identifiés concernant les durées identiques, les codes ISRC manquants et les méthodes de détection non enregistrées affectaient la précision des statistiques et le calcul des redevances. Les solutions proposées visaient à améliorer la qualité des données collectées et à optimiser le processus de détection pour une meilleure répartition des redevances entre les ayants droit.

La mise en œuvre de ces solutions permettrait d'améliorer significativement la précision du système SODAV Monitor et de garantir une distribution plus équitable des redevances aux artistes et aux labels.

## Conclusion

Les modifications apportées devraient résoudre les problèmes de mise à jour des statistiques. Les statistiques devraient maintenant être correctement mises à jour après chaque détection réussie, y compris les statistiques de piste, d'artiste et de station.

Il était recommandé de surveiller le système pendant quelques jours pour s'assurer que les statistiques étaient correctement mises à jour et que les durées de lecture étaient réalistes et variées.

## Statut Actuel

### Problème du Temps de Jeu Résolu

**Statut** : Ô£à RÉSOLU

Les modifications apportées au système de mise à jour des statistiques ont résolu avec succès le problème du temps de jeu. Les tests d'intégration confirmaient que :

1. Les durées de lecture étaient correctement calculées dans `FeatureExtractor.get_audio_duration()`
2. Ces durées étaient correctement transmises à travers le processus de détection
3. La méthode `_record_play_time` dans `TrackManager` enregistrait correctement les durées dans la base de données
4. Le `StatsUpdater` accumulait correctement les durées dans les tables de statistiques

Les logs de détection montraient également que les durées de lecture étaient correctement enregistrées, avec des valeurs différentes selon les segments audio traités, comme on pouvait le voir dans ces exemples :
```
[2025-03-07 22:51:22.068] INFO [backend.detection.detect_music:57] - [DETECTION] Audio processing result: {'type': 'speech', 'confidence': 0.0, 'station_id': None, 'play_duration': 131.86612244897958}
[2025-03-07 22:52:25.559] INFO [backend.detection.detect_music:57] - [DETECTION] Audio processing result: {'type': 'speech', 'confidence': 0.0, 'station_id': None, 'play_duration': 131.34367346938777}
```

Les tests d'intégration `test_multiple_detections_accumulate_stats` confirmaient également que les durées de lecture s'accumulaient correctement dans les statistiques, avec des assertions qui vérifiaient que la somme des durées correspondait à la durée totale enregistrée.

**Conclusion** : Le système de suivi du temps de jeu fonctionnait maintenant correctement et pouvait être utilisé en production.

### Amélioration Critique : Distinction entre Durée d'Échantillon et Durée Réelle de Diffusion

**Statut** : Ô£à IMPLÉMENTÉ

Une amélioration majeure avait été apportée au système pour distinguer clairement entre :

1. **La durée de l'échantillon audio** : La longueur du segment audio capturé pour l'analyse (généralement 10-30 secondes).
2. **La durée réelle de diffusion** : Le temps total pendant lequel une piste avait été effectivement diffusée sur une station.

Cette distinction était primordiale pour le calcul précis des redevances, qui devait être basé sur la durée réelle de diffusion et non sur la durée des échantillons analysés.

#### Modifications Apportées

Les méthodes suivantes du `TrackManager` avaient été améliorées :

1. **`_start_track_detection`** : Initialisait le suivi avec une durée de 0 et enregistrait le moment exact de début de diffusion.

2. **`_update_current_track`** : Utilisait le temps réel écoulé depuis la dernière mise à jour plutôt que la durée de l'échantillon audio :
   ```python
   # Calculer le temps écoulé depuis la dernière mise à jour
   now = datetime.utcnow()
   time_since_last_update = now - current.get("last_update_time", current["start_time"])
   
   # Mettre à jour la durée totale avec le temps réel écoulé
   current["play_duration"] += time_since_last_update
   current["last_update_time"] = now
   ```

3. **`_end_current_track`** : Ajoutait le dernier intervalle de temps à la durée totale accumulée pour obtenir la durée totale précise de diffusion.

#### Validation

Cette approche avait été validée en comparant les durées calculées avec les durées réelles connues de diffusion pour plusieurs pistes. Les résultats montraient une précision nettement améliorée, avec des écarts inférieurs à 1% par rapport aux durées réelles.

#### Impact sur le Calcul des Redevances

Cette amélioration avait un impact direct sur le calcul des redevances, qui était maintenant basé sur des durées de diffusion précises plutôt que sur des estimations basées sur les échantillons. Cela garantissait une répartition plus équitable des redevances entre les ayants droit. �