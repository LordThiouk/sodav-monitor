# Migration : Améliorations de la Détection de Pistes

## Résumé

Cette migration ajoute des champs supplémentaires aux modèles `Track` et `TrackDetection` pour améliorer la capture d'informations lors de la détection musicale. Ces améliorations permettent de stocker des informations plus détaillées sur les pistes détectées et de réduire la dépendance aux API externes.

## Changements apportés

### 1. Ajout de champs au modèle `Track`

Deux nouveaux champs ont été ajoutés au modèle `Track` :

- `release_date` : Pour stocker la date de sortie de la piste (type `String`, nullable)
- `genre` : Pour stocker le genre musical de la piste (type `String`, nullable)

### 2. Ajout de champ au modèle `TrackDetection`

Un nouveau champ a été ajouté au modèle `TrackDetection` :

- `detection_method` : Pour enregistrer la méthode de détection utilisée (type `String`, nullable)
  - Valeurs possibles : "local", "musicbrainz", "acoustid", "audd"

## Scripts de migration

Deux scripts de migration ont été créés pour appliquer ces changements à la base de données :

1. `backend/models/migrations/add_track_fields.py` : Ajoute les champs `release_date` et `genre` à la table `tracks`
2. `backend/models/migrations/add_detection_method.py` : Ajoute le champ `detection_method` à la table `track_detections`

## Exécution des migrations

Pour appliquer ces migrations, exécutez les commandes suivantes depuis la racine du projet :

```bash
python backend/models/migrations/add_track_fields.py
python backend/models/migrations/add_detection_method.py
```

## Améliorations fonctionnelles

Ces changements permettent les améliorations fonctionnelles suivantes :

1. **Capture d'informations supplémentaires** :
   - ISRC des pistes
   - Label des artistes
   - Date de sortie des pistes
   - Genre musical

2. **Traçabilité des détections** :
   - Méthode de détection utilisée pour chaque détection
   - Temps de jeu exact de chaque piste

3. **Réduction de la dépendance aux API externes** :
   - Stockage des empreintes digitales pour les détections futures
   - Utilisation prioritaire de la détection locale

## Impact sur le code existant

Les méthodes suivantes ont été améliorées pour utiliser les nouveaux champs :

- `find_local_match` : Utilise les empreintes digitales stockées pour la détection locale
- `find_acoustid_match` : Capture l'ISRC, le label et la date de sortie
- `find_musicbrainz_match` : Capture l'ISRC, le label et la date de sortie
- `find_audd_match` : Capture l'ISRC, le label et la date de sortie

Une nouvelle méthode a été ajoutée :

- `_record_play_time` : Enregistre le temps de jeu exact d'une piste sur une station

## Tests

Des tests ont été créés pour vérifier le bon fonctionnement des nouvelles fonctionnalités :

- `backend/scripts/detection/test_detection_hierarchy.py` : Teste le processus de détection hiérarchique complet
- `backend/scripts/detection/test_audd_detection.py` : Teste spécifiquement la détection AudD avec les nouvelles fonctionnalités

## Documentation

La documentation a été mise à jour pour refléter ces changements :

- `docs/external_services.md` : Documentation complète sur les services externes de détection musicale
- `docs/migrations/track_detection_enhancements.md` : Ce document de migration
- `docs/fingerprint_reuse.md` : Documentation détaillée sur la fonctionnalité de réutilisation des empreintes digitales

## Modifications du code

### 1. Ajout du paramètre `features` à `process_stream`

La méthode `process_stream` de la classe `AudioProcessor` a été modifiée pour accepter un paramètre optionnel `features` :

```python
async def process_stream(self, audio_data: np.ndarray, station_id: Optional[int] = None, features: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
```

Cette modification permet de passer directement des caractéristiques audio pré-calculées, y compris une empreinte digitale spécifique, ce qui est essentiel pour la réutilisation des empreintes.

### 2. Modification de l'extraction des caractéristiques

Le code d'extraction des caractéristiques a été modifié pour utiliser les caractéristiques fournies si elles existent :

```python
# 1. Extraire les caractéristiques audio si elles ne sont pas fournies
if features is None:
    features = self.feature_extractor.extract_features(audio_data)
```

### 3. Amélioration de la détection locale

La méthode `find_local_match` a été améliorée pour rechercher d'abord une correspondance exacte de l'empreinte digitale :

```python
# Rechercher une correspondance exacte
exact_match = db.query(Track).filter(Track.fingerprint == fingerprint).first()
if exact_match:
    # Traitement de la correspondance exacte
```

## Tests de validation

Un nouveau script de test a été créé pour valider la fonctionnalité de réutilisation des empreintes digitales :

- `backend/scripts/detection/test_fingerprint_reuse.py`

Ce script teste le processus complet de réutilisation des empreintes :
1. Création d'une piste avec une empreinte unique
2. Simulation d'une détection avec la même empreinte
3. Vérification que la piste est correctement identifiée via la détection locale

## Prochaines étapes

- Optimisation de la recherche d'empreintes pour de grandes bases de données
- Implémentation d'un système de mise en cache des empreintes fréquemment utilisées
- Développement d'un système de vérification de l'intégrité des empreintes
- Amélioration de la robustesse face aux variations de qualité audio 