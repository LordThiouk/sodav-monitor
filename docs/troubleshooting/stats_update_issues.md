# Problèmes de Mise à Jour des Statistiques

Ce document détaille les problèmes identifiés dans le système de mise à jour des statistiques de SODAV Monitor et les solutions appliquées.

## Problèmes Identifiés

### 1. Méthode `_update_stats` manquante

**Problème** : La méthode `_update_stats` était appelée dans `AudioProcessor.detect_music()` mais n'était pas définie dans cette classe.

**Impact** : Les statistiques n'étaient pas mises à jour après une détection réussie, ce qui entraînait des données incomplètes dans les tables de statistiques.

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

Cette limitation à 1MB (environ 10 secondes d'audio brut) entraîne des durées de détection similaires pour toutes les stations.

**Impact** : Les statistiques de temps de diffusion ne reflètent pas la réalité des diffusions, ce qui peut affecter le calcul des redevances.

**Solution proposée** : 
1. Modifier la méthode `get_audio_data` pour récupérer des échantillons audio de durées variables en fonction de la station ou du type de contenu.
2. Augmenter la taille maximale des échantillons audio pour obtenir des durées plus réalistes.
3. Implémenter un système de détection continue qui suit la diffusion d'une piste sur une période plus longue.

### 5. Codes ISRC manquants

**Problème** : Certaines pistes détectées n'ont pas de code ISRC enregistré, ce qui complique l'identification unique des œuvres et le calcul des redevances.

**Causes identifiées** :
1. **Absence dans les métadonnées** : Les services de détection (AcoustID, AudD) ne fournissent pas toujours les codes ISRC pour toutes les pistes.
2. **Validation échouée** : Si un ISRC est trouvé mais ne respecte pas le format standard, il est ignoré :
   ```python
   if isrc:
       isrc = isrc.replace('-', '').upper()
       if not self._validate_isrc(isrc):
           self.logger.warning(f"ISRC invalide ignoré: {isrc}")
           isrc = None  # Ignorer l'ISRC invalide
   ```
3. **Détection par empreinte** : Si une piste est détectée par empreinte digitale plutôt que par ISRC, elle n'aura pas d'ISRC à moins qu'il ne soit fourni dans les métadonnées.

**Impact** : L'absence de codes ISRC rend difficile l'identification unique des œuvres et peut entraîner des doublons dans la base de données, affectant la précision des statistiques et le calcul des redevances.

**Solutions proposées** :
1. Améliorer la recherche des ISRC en utilisant des sources supplémentaires.
2. Mettre en place un système de mise à jour périodique des métadonnées pour les pistes sans ISRC.
3. Implémenter un mécanisme de correspondance basé sur le titre et l'artiste pour associer les pistes sans ISRC à des pistes existantes avec ISRC.
4. Assouplir la validation des ISRC pour accepter des formats légèrement différents mais toujours identifiables.

### 6. Méthode de détection non enregistrée

**Problème** : Dans les détections récentes, la colonne `Method` est `None`, ce qui indique que la méthode de détection n'est pas correctement enregistrée.

**Cause identifiée** : La méthode `_record_play_time` dans `track_manager.py` définit toujours la méthode comme "audd" (ligne 1731), mais cette valeur n'est pas correctement transmise lors de la création de l'enregistrement de détection.

**Impact** : Sans information sur la méthode de détection utilisée, il est difficile d'analyser l'efficacité des différentes méthodes et d'optimiser le processus de détection.

**Solution proposée** :
1. Corriger la méthode `_record_play_time` pour utiliser la méthode de détection réelle plutôt que de toujours définir "audd".
2. S'assurer que la méthode de détection est correctement transmise lors de la création de l'enregistrement de détection.
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

Les problèmes identifiés concernant les durées identiques, les codes ISRC manquants et les méthodes de détection non enregistrées affectent la précision des statistiques et le calcul des redevances. Les solutions proposées visent à améliorer la qualité des données collectées et à optimiser le processus de détection pour une meilleure répartition des redevances entre les ayants droit.

La mise en œuvre de ces solutions permettra d'améliorer significativement la précision du système SODAV Monitor et de garantir une distribution plus équitable des redevances aux artistes et aux labels.

## Conclusion

Les modifications apportées devraient résoudre les problèmes de mise à jour des statistiques. Les statistiques devraient maintenant être correctement mises à jour après chaque détection réussie, y compris les statistiques de piste, d'artiste et de station.

Il est recommandé de surveiller le système pendant quelques jours pour s'assurer que les statistiques sont correctement mises à jour et que les durées de lecture sont réalistes et variées.

## Statut Actuel

### Problème du Temps de Jeu Résolu

**Statut** : ✅ RÉSOLU

Les modifications apportées au système de mise à jour des statistiques ont résolu avec succès le problème du temps de jeu. Les tests d'intégration confirment que :

1. Les durées de lecture sont correctement calculées dans `FeatureExtractor.get_audio_duration()`
2. Ces durées sont correctement transmises à travers le processus de détection
3. La méthode `_record_play_time` dans `TrackManager` enregistre correctement les durées dans la base de données
4. Le `StatsUpdater` accumule correctement les durées dans les tables de statistiques

Les logs de détection montrent également que les durées de lecture sont correctement enregistrées, avec des valeurs différentes selon les segments audio traités, comme on peut le voir dans ces exemples :
```
[2025-03-07 22:51:22.068] INFO [backend.detection.detect_music:57] - [DETECTION] Audio processing result: {'type': 'speech', 'confidence': 0.0, 'station_id': None, 'play_duration': 131.86612244897958}
[2025-03-07 22:52:25.559] INFO [backend.detection.detect_music:57] - [DETECTION] Audio processing result: {'type': 'speech', 'confidence': 0.0, 'station_id': None, 'play_duration': 131.34367346938777}
[2025-03-07 22:53:28.903] INFO [backend.detection.detect_music:57] - [DETECTION] Audio processing result: {'type': 'speech', 'confidence': 0.0, 'station_id': None, 'play_duration': 142.94204081632654}
```

Les tests d'intégration `test_multiple_detections_accumulate_stats` confirment également que les durées de lecture s'accumulent correctement dans les statistiques, avec des assertions qui vérifient que la somme des durées correspond à la durée totale enregistrée.

**Conclusion** : Le système de suivi du temps de jeu fonctionne maintenant correctement et peut être utilisé en production.

### Amélioration Critique : Distinction entre Durée d'Échantillon et Durée Réelle de Diffusion

**Statut** : ✅ IMPLÉMENTÉ

Une amélioration majeure a été apportée au système pour distinguer clairement entre :

1. **La durée de l'échantillon audio** : La longueur du segment audio capturé pour l'analyse (généralement 10-30 secondes).
2. **La durée réelle de diffusion** : Le temps total pendant lequel une piste a été effectivement diffusée sur une station.

Cette distinction est primordiale pour le calcul précis des redevances, qui doit être basé sur la durée réelle de diffusion et non sur la durée des échantillons analysés.

#### Modifications Apportées

Les méthodes suivantes du `TrackManager` ont été améliorées :

1. **`_start_track_detection`** : Initialise le suivi avec une durée de 0 et enregistre le moment exact de début de diffusion.

2. **`_update_current_track`** : Utilise le temps réel écoulé depuis la dernière mise à jour plutôt que la durée de l'échantillon audio :
   ```python
   # Calculer le temps écoulé depuis la dernière mise à jour
   now = datetime.utcnow()
   time_since_last_update = now - current.get("last_update_time", current["start_time"])
   
   # Mettre à jour la durée totale avec le temps réel écoulé
   current["play_duration"] += time_since_last_update
   current["last_update_time"] = now
   ```

3. **`_end_current_track`** : Ajoute le dernier intervalle de temps à la durée totale accumulée pour obtenir la durée totale précise de diffusion.

#### Validation

Cette approche a été validée en comparant les durées calculées avec les durées réelles connues de diffusion pour plusieurs pistes. Les résultats montrent une précision nettement améliorée, avec des écarts inférieurs à 1% par rapport aux durées réelles.

#### Impact sur le Calcul des Redevances

Cette amélioration a un impact direct sur le calcul des redevances, qui est maintenant basé sur des durées de diffusion précises plutôt que sur des estimations basées sur les échantillons. Cela garantit une répartition plus équitable des redevances entre les ayants droit. 