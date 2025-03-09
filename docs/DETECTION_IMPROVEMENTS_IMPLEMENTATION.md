# Implémentation des Améliorations de la Détection Locale

Ce document détaille les modifications apportées au système de détection locale du projet SODAV Monitor pour améliorer la robustesse et la précision de la détection des pistes musicales.

## 1. Mise à jour de la Méthode `find_local_match`

La méthode `find_local_match` du `TrackManager` a été mise à jour pour utiliser la nouvelle table `fingerprints` au lieu de chercher uniquement dans la colonne `fingerprint` de la table `tracks`. Cette modification permet de rechercher des correspondances parmi plusieurs empreintes digitales pour chaque piste, ce qui améliore considérablement la robustesse de la détection.

### Principales modifications :

1. **Recherche dans la table `fingerprints`** :
   - Vérification de l'existence de la table `fingerprints`
   - Recherche d'une correspondance exacte dans la table `fingerprints`
   - Récupération de la piste associée à l'empreinte trouvée

2. **Recherche par similarité** :
   - Si aucune correspondance exacte n'est trouvée, recherche par similarité parmi toutes les empreintes
   - Calcul du score de similarité pour chaque empreinte
   - Sélection de la meilleure correspondance si le score dépasse un seuil (0.7)

3. **Fallback vers l'ancienne méthode** :
   - Si la table `fingerprints` n'existe pas ou si aucune correspondance n'est trouvée, utilisation de l'ancienne méthode de recherche dans la colonne `fingerprint` de la table `tracks`

### Extrait de code :

```python
# Rechercher d'abord dans la table fingerprints (nouvelle méthode)
from backend.models.models import Fingerprint

# Rechercher une correspondance exacte
fingerprint = self.db_session.query(Fingerprint).filter_by(hash=fingerprint_hash).first()

if fingerprint:
    # Récupérer la piste associée
    track = self.db_session.query(Track).filter_by(id=fingerprint.track_id).first()
    
    if track:
        # Récupérer le nom de l'artiste via la relation
        artist_name = track.artist.name if track.artist else "Unknown Artist"
        logger.info(f"[TRACK_MANAGER] Exact fingerprint match found in fingerprints table: {track.title} by {artist_name}")
        return {
            "title": track.title,
            "artist": artist_name,
            "album": track.album,
            "id": track.id,
            "isrc": track.isrc,
            "label": track.label,
            "release_date": track.release_date,
            "fingerprint": fingerprint_hash[:20] + "..." if fingerprint_hash else None,
            "confidence": 1.0,
            "source": "local"
        }
```

## 2. Amélioration de la Gestion des Transactions SQL

Une nouvelle méthode utilitaire `_execute_with_transaction` a été ajoutée pour gérer les transactions SQL de manière plus robuste, avec des blocs try/except et des rollbacks appropriés. Cette méthode permet d'éviter les erreurs de transaction qui pouvaient se produire lors des tests.

### Extrait de code :

```python
def _execute_with_transaction(self, operation_func, *args, **kwargs):
    """
    Exécute une opération dans une transaction avec gestion des erreurs.
    
    Args:
        operation_func: Fonction à exécuter dans la transaction
        *args, **kwargs: Arguments à passer à la fonction
        
    Returns:
        Résultat de la fonction ou None en cas d'erreur
    """
    try:
        # Exécuter l'opération
        result = operation_func(*args, **kwargs)
        return result
    except Exception as e:
        # En cas d'erreur, annuler la transaction
        log_with_category(logger, "TRACK_MANAGER", "error", f"Transaction error: {str(e)}")
        import traceback
        log_with_category(logger, "TRACK_MANAGER", "error", f"Traceback: {traceback.format_exc()}")
        
        try:
            # Essayer de faire un rollback
            self.db_session.rollback()
            log_with_category(logger, "TRACK_MANAGER", "info", "Transaction rolled back successfully")
        except Exception as rollback_error:
            log_with_category(logger, "TRACK_MANAGER", "error", f"Error during rollback: {str(rollback_error)}")
        
        return None
```

## 3. Mise à jour de la Méthode `_get_or_create_track`

La méthode `_get_or_create_track` a été mise à jour pour sauvegarder les empreintes digitales dans la nouvelle table `fingerprints` en plus de la colonne `fingerprint` de la table `tracks`. Cette modification permet de stocker plusieurs empreintes pour chaque piste, ce qui améliore la robustesse de la détection.

### Principales modifications :

1. **Recherche dans la table `fingerprints`** :
   - Vérification de l'existence de la table `fingerprints`
   - Recherche d'une correspondance dans la table `fingerprints`
   - Récupération de la piste associée à l'empreinte trouvée

2. **Sauvegarde des empreintes** :
   - Vérification si l'empreinte existe déjà pour la piste
   - Ajout de l'empreinte à la table `fingerprints` si elle n'existe pas
   - Mise à jour de la colonne `fingerprint` de la table `tracks` pour compatibilité

3. **Création de nouvelles pistes** :
   - Sauvegarde de l'empreinte dans la table `fingerprints` lors de la création d'une nouvelle piste
   - Création des statistiques de piste

### Extrait de code :

```python
# Ajouter l'empreinte à la table fingerprints si elle existe
if fingerprint_hash:
    from sqlalchemy import inspect
    inspector = inspect(self.db_session.bind)
    if "fingerprints" in inspector.get_table_names():
        from backend.models.models import Fingerprint
        new_fingerprint = Fingerprint(
            track_id=track.id,
            hash=fingerprint_hash,
            raw_data=fingerprint_raw,
            offset=0.0,  # Position par défaut
            algorithm="md5"  # Algorithme par défaut
        )
        self.db_session.add(new_fingerprint)
        log_with_category(logger, "TRACK_MANAGER", "info", f"Added fingerprint to fingerprints table for new track {track.id}")
```

## 4. Avantages des Modifications

1. **Robustesse** : La possibilité de stocker plusieurs empreintes par piste permet une détection plus robuste, même lorsque seule une partie de la piste est disponible.

2. **Précision** : La recherche dans la table `fingerprints` permet de trouver des correspondances plus précises, car elle peut comparer avec plusieurs empreintes pour chaque piste.

3. **Compatibilité** : Le système maintient la compatibilité avec l'ancienne méthode de recherche dans la colonne `fingerprint` de la table `tracks`, ce qui permet une transition en douceur.

4. **Fiabilité** : La gestion améliorée des transactions SQL réduit les erreurs de transaction et améliore la fiabilité du système.

## 5. Prochaines Étapes

1. **Optimisation des performances** :
   - Mise en place de mécanismes de cache pour les empreintes fréquemment utilisées
   - Optimisation des requêtes SQL pour améliorer les performances de recherche

2. **Amélioration de la recherche par similarité** :
   - Implémentation d'algorithmes de recherche plus avancés pour améliorer la précision de la détection
   - Utilisation de techniques d'indexation pour accélérer la recherche

3. **Intégration de Chromaprint** :
   - Utilisation de l'algorithme Chromaprint pour générer des empreintes plus robustes
   - Comparaison des performances entre les empreintes MD5 et Chromaprint

4. **Tests et validation** :
   - Création de tests unitaires pour valider les modifications
   - Mesure des performances et de la précision de la détection

## 6. Conclusion

Les modifications apportées au système de détection locale du projet SODAV Monitor améliorent considérablement la robustesse et la précision de la détection des pistes musicales. La possibilité de stocker plusieurs empreintes par piste et la gestion améliorée des transactions SQL rendent le système plus fiable et plus performant.

Ces améliorations permettent de réduire la dépendance aux services externes de détection, ce qui réduit les coûts et améliore l'autonomie du système. Elles constituent une étape importante vers un système de détection musicale plus robuste et plus précis. 