# Migration : Contrainte d'Unicité sur l'ISRC

## Résumé

Cette migration ajoute une contrainte d'unicité sur la colonne `isrc` de la table `tracks` pour garantir qu'un même code ISRC ne peut pas être associé à plusieurs pistes différentes. Cette amélioration assure l'intégrité des données et évite la duplication des pistes dans la base de données.

## Problème Résolu

Avant cette migration, il était possible d'avoir plusieurs entrées dans la table `tracks` avec le même code ISRC, ce qui pouvait entraîner :
- Des doublons de pistes dans la base de données
- Des statistiques de lecture incorrectes (réparties entre plusieurs entrées pour la même piste)
- Des incohérences dans les rapports générés

## Changements Apportés

### 1. Ajout de la Contrainte d'Unicité

Une contrainte d'unicité a été ajoutée à la colonne `isrc` de la table `tracks` pour garantir qu'un même code ISRC ne peut pas être associé à plusieurs pistes.

### 2. Nettoyage des Doublons Existants

Avant d'ajouter la contrainte, un processus de nettoyage a été mis en place pour :
- Identifier les codes ISRC dupliqués
- Conserver une seule entrée pour chaque code ISRC (la plus complète ou la plus récente)
- Mettre à jour les références dans les autres tables pour pointer vers l'entrée conservée
- Supprimer les entrées dupliquées

## Scripts de Migration

Un script de migration a été créé pour appliquer ces changements à la base de données :

- `backend/models/migrations/add_isrc_unique_constraint.py` : Nettoie les doublons d'ISRC et ajoute la contrainte d'unicité

## Exécution de la Migration

Pour appliquer cette migration, exécutez la commande suivante depuis la racine du projet :

```bash
PYTHONPATH=/chemin/vers/sodav-monitor python -m backend.models.migrations.add_isrc_unique_constraint
```

## Améliorations Fonctionnelles

Ces changements permettent les améliorations fonctionnelles suivantes :

1. **Intégrité des données** :
   - Garantie qu'un même code ISRC ne peut pas être associé à plusieurs pistes
   - Réduction des doublons dans la base de données

2. **Précision des statistiques** :
   - Toutes les détections d'une même piste sont associées à une seule entrée
   - Les statistiques de lecture sont consolidées pour chaque piste unique

3. **Amélioration de la détection** :
   - Utilisation de l'ISRC comme identifiant principal pour retrouver les pistes existantes
   - Réduction des faux positifs dans le processus de détection

## Impact sur le Code Existant

Les méthodes suivantes ont été améliorées pour utiliser l'ISRC comme critère principal d'identification :

- `find_acoustid_match` : Vérifie d'abord si une piste avec le même ISRC existe déjà
- `find_audd_match` : Vérifie d'abord si une piste avec le même ISRC existe déjà

## Tests

Des tests ont été créés pour vérifier le bon fonctionnement de la contrainte d'unicité :

- Test de détection avec des pistes ayant le même ISRC
- Vérification que les statistiques de lecture sont correctement mises à jour pour les pistes existantes

## Modifications du Code

### 1. Modification de la Méthode `find_acoustid_match`

La méthode `find_acoustid_match` a été modifiée pour vérifier d'abord si une piste avec le même ISRC existe déjà :

```python
# Si nous avons un ISRC valide, vérifier d'abord si une piste avec cet ISRC existe déjà
existing_track = None
if isrc:
    existing_track = self.db_session.query(Track).filter(Track.isrc == isrc).first()
    if existing_track:
        self.logger.info(f"Found existing track with ISRC {isrc}: {existing_track.title} by artist ID {existing_track.artist_id}")
        
        # Récupérer l'artiste
        artist = self.db_session.query(Artist).filter(Artist.id == existing_track.artist_id).first()
        artist_name_from_db = artist.name if artist else "Unknown Artist"
        
        # Mettre à jour les statistiques si station_id est fourni
        if station_id:
            self._record_play_time(station_id, existing_track.id, play_duration)
        
        # Retourner les informations de la piste existante
        return {
            "track": {
                "id": existing_track.id,
                "title": existing_track.title,
                "artist": artist_name_from_db,
                "album": existing_track.album,
                "isrc": existing_track.isrc,
                "label": existing_track.label,
                "release_date": existing_track.release_date
            },
            "confidence": 0.9,  # Haute confiance pour une correspondance par ISRC
            "source": "acoustid",
            "detection_method": "acoustid",
            "play_duration": play_duration
        }
```

### 2. Modification de la Méthode `find_audd_match`

La méthode `find_audd_match` a été modifiée de manière similaire pour vérifier d'abord si une piste avec le même ISRC existe déjà :

```python
# Si nous avons un ISRC valide, vérifier d'abord si une piste avec cet ISRC existe déjà
existing_track = None
if isrc:
    existing_track = self.db_session.query(Track).filter(Track.isrc == isrc).first()
    if existing_track:
        self.logger.info(f"Found existing track with ISRC {isrc}: {existing_track.title} by artist ID {existing_track.artist_id}")
        
        # Récupérer l'artiste
        artist = self.db_session.query(Artist).filter(Artist.id == existing_track.artist_id).first()
        artist_name_from_db = artist.name if artist else "Unknown Artist"
        
        # Mettre à jour les statistiques si station_id est fourni
        if station_id:
            self._record_play_time(station_id, existing_track.id, play_duration)
        
        # Retourner les informations de la piste existante
        return {
            "track": {
                "id": existing_track.id,
                "title": existing_track.title,
                "artist": artist_name_from_db,
                "album": existing_track.album,
                "isrc": existing_track.isrc,
                "label": existing_track.label,
                "release_date": existing_track.release_date
            },
            "confidence": 0.9,  # Haute confiance pour une correspondance par ISRC
            "source": "audd",
            "detection_method": "audd",
            "play_duration": play_duration
        }
```

## Prochaines Étapes

- Optimisation de la recherche par ISRC pour de grandes bases de données
- Implémentation d'un système de vérification de la validité des codes ISRC
- Développement d'un système de fusion des pistes dupliquées existantes
- Amélioration de l'extraction des codes ISRC à partir des métadonnées des services externes 