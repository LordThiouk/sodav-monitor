# Détails d'Implémentation des Améliorations de Détection

Ce document détaille les améliorations spécifiques apportées au système de détection musicale du projet SODAV Monitor, en particulier l'intégration de Chromaprint, l'amélioration de l'extraction des métadonnées et la gestion des erreurs.

## 1. Améliorations de la Détection avec AcoustID

### 1.1 Initialisation Robuste du Service AcoustID

La classe `TrackManager` a été améliorée pour initialiser correctement les services externes (AcoustID et AudD) lors de sa création :

```python
def __init__(self, db_session: Session, feature_extractor=None):
    """Initialize TrackManager."""
    self.db_session = db_session
    self.logger = logging.getLogger(__name__)
    self.current_tracks = {}  # station_id -> current track info
    self.feature_extractor = feature_extractor
    
    # Initialize external services
    acoustid_api_key = os.environ.get("ACOUSTID_API_KEY")
    audd_api_key = os.environ.get("AUDD_API_KEY")
    
    # Initialize AcoustID service
    if acoustid_api_key:
        try:
            self.acoustid_service = AcoustIDService(acoustid_api_key)
            self.logger.info("AcoustID service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize AcoustID service: {e}")
            self.acoustid_service = None
    else:
        self.logger.warning("ACOUSTID_API_KEY not found in environment variables")
        self.acoustid_service = None
    
    # Initialize AudD service
    if audd_api_key:
        try:
            self.audd_service = AuddService(audd_api_key)
            self.logger.info("AudD service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize AudD service: {e}")
            self.audd_service = None
    else:
        self.logger.warning("AUDD_API_KEY not found in environment variables")
        self.audd_service = None
```

### 1.2 Amélioration de la Méthode `find_acoustid_match`

La méthode `find_acoustid_match` a été entièrement réécrite pour :
- Utiliser le service AcoustID initialisé dans le constructeur
- Extraire correctement les métadonnées (ISRC, label, date de sortie)
- Utiliser `_get_or_create_track` pour créer ou mettre à jour les pistes
- Enregistrer la méthode de détection dans la base de données
- Gérer les erreurs de manière robuste avec des logs détaillés

```python
async def find_acoustid_match(self, audio_features: Dict[str, Any], station_id=None) -> Optional[Dict[str, Any]]:
    """
    Recherche une correspondance avec le service AcoustID.
    
    Args:
        audio_features: Caractéristiques audio extraites
        station_id: ID de la station (optionnel)
        
    Returns:
        Dictionnaire avec les informations de la piste ou None si aucune correspondance
    """
    if not self.acoustid_service:
        self.logger.warning("AcoustID service not initialized")
        return None
    
    try:
        # Convertir les caractéristiques en audio
        audio_data = self._convert_features_to_audio(audio_features)
        if not audio_data:
            self.logger.error("Failed to convert features to audio for AcoustID detection")
            return None
        
        # Détecter avec AcoustID
        self.logger.info(f"Detecting with AcoustID for station_id={station_id}")
        result = await self.acoustid_service.detect_track_with_retry(audio_data, max_retries=3)
        
        # ... (extraction des métadonnées et création/mise à jour de la piste)
    except Exception as e:
        self.logger.error(f"Error in AcoustID detection: {e}")
        import traceback
        self.logger.error(f"Traceback: {traceback.format_exc()}")
        return None
```

## 2. Améliorations de la Détection avec AudD

### 2.1 Amélioration de la Méthode `find_audd_match`

La méthode `find_audd_match` a été entièrement réécrite pour :
- Utiliser le service AudD initialisé dans le constructeur
- Extraire correctement les métadonnées (ISRC, label, date de sortie) à partir de différentes sources (Apple Music, Spotify, Deezer)
- Utiliser `_get_or_create_track` pour créer ou mettre à jour les pistes
- Enregistrer la méthode de détection dans la base de données
- Gérer les erreurs de manière robuste avec des logs détaillés

```python
async def find_audd_match(self, audio_features, station_id=None):
    """
    Recherche une correspondance avec le service AudD.
    
    Args:
        audio_features: Caractéristiques audio extraites
        station_id: ID de la station (optionnel)
        
    Returns:
        Dictionnaire avec les informations de la piste ou None si aucune correspondance
    """
    if not self.audd_service:
        self.logger.warning("AudD service not initialized")
        return None
    
    try:
        # Convertir les caractéristiques en audio
        audio_data = self._convert_features_to_audio(audio_features)
        if not audio_data:
            self.logger.error("Failed to convert features to audio for AudD detection")
            return None
        
        # Détecter avec AudD
        self.logger.info(f"Detecting with AudD for station_id={station_id}")
        result = await self.audd_service.detect_track_with_retry(audio_data, max_retries=3)
        
        # ... (extraction des métadonnées et création/mise à jour de la piste)
    except Exception as e:
        self.logger.error(f"Error in AudD detection: {e}")
        import traceback
        self.logger.error(f"Traceback: {traceback.format_exc()}")
        return None
```

### 2.2 Extraction Améliorée des Métadonnées

L'extraction des métadonnées a été améliorée pour vérifier plusieurs sources possibles :

```python
# Extraire l'ISRC - vérifier plusieurs sources possibles
isrc = None
# Vérifier dans le résultat principal
if "isrc" in result:
    isrc = result["isrc"]
    self.logger.info(f"ISRC found in main result: {isrc}")

# Vérifier dans Apple Music
elif "apple_music" in result and result["apple_music"]:
    if "isrc" in result["apple_music"]:
        isrc = result["apple_music"]["isrc"]
        self.logger.info(f"ISRC found in Apple Music: {isrc}")

# Vérifier dans Spotify
elif "spotify" in result and result["spotify"]:
    if "external_ids" in result["spotify"] and "isrc" in result["spotify"]["external_ids"]:
        isrc = result["spotify"]["external_ids"]["isrc"]
        self.logger.info(f"ISRC found in Spotify: {isrc}")

# Vérifier dans Deezer
elif "deezer" in result and result["deezer"]:
    if "isrc" in result["deezer"]:
        isrc = result["deezer"]["isrc"]
        self.logger.info(f"ISRC found in Deezer: {isrc}")
```

## 3. Amélioration de la Gestion des Transactions SQL

### 3.1 Méthode `_execute_with_transaction`

Une nouvelle méthode utilitaire `_execute_with_transaction` a été ajoutée pour gérer les transactions SQL de manière robuste :

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
        
        # Valider la transaction
        self.db_session.commit()
        return result
    except Exception as e:
        # En cas d'erreur, annuler la transaction
        self.logger.error(f"Transaction error: {str(e)}")
        import traceback
        self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        try:
            # Essayer de faire un rollback
            self.db_session.rollback()
            self.logger.info("Transaction rolled back successfully")
        except Exception as rollback_error:
            self.logger.error(f"Error during rollback: {str(rollback_error)}")
        
        return None
```

### 3.2 Utilisation de `_execute_with_transaction` dans `_get_or_create_track`

La méthode `_get_or_create_track` a été modifiée pour utiliser `_execute_with_transaction` :

```python
if track:
    # Mettre à jour la piste existante avec les nouvelles informations
    def update_track():
        # ... (mise à jour de la piste)
        return track
    
    return self._execute_with_transaction(update_track)
else:
    # Créer une nouvelle piste
    def create_track():
        # ... (création de la piste)
        return track
    
    return self._execute_with_transaction(create_track)
```

## 4. Amélioration de la Conversion des Caractéristiques Audio

### 4.1 Méthode `_convert_features_to_audio`

La méthode `_convert_features_to_audio` a été améliorée pour gérer différents formats d'entrée :

```python
def _convert_features_to_audio(self, features: Dict[str, Any]) -> Optional[bytes]:
    """
    Convertit les caractéristiques audio en données audio brutes.
    
    Args:
        features: Dictionnaire de caractéristiques audio
        
    Returns:
        Données audio brutes (bytes) ou None en cas d'erreur
    """
    try:
        # Vérifier si les données audio brutes sont déjà disponibles
        if "raw_audio" in features and features["raw_audio"]:
            self.logger.info(f"Using raw audio data from features ({len(features['raw_audio'])} bytes)")
            return features["raw_audio"]
        
        # Vérifier si le chemin du fichier audio est disponible
        if "audio_file" in features and features["audio_file"]:
            audio_file = features["audio_file"]
            if os.path.exists(audio_file):
                self.logger.info(f"Reading audio data from file: {audio_file}")
                with open(audio_file, "rb") as f:
                    return f.read()
            else:
                self.logger.error(f"Audio file not found: {audio_file}")
        
        # Vérifier si les données audio sont disponibles sous forme de tableau numpy
        if "audio_data" in features and features["audio_data"] is not None:
            # ... (conversion du tableau numpy en bytes)
        
        self.logger.error("No convertible audio data found in features")
        return None
    
    except Exception as e:
        self.logger.error(f"Error converting features to audio: {e}")
        import traceback
        self.logger.error(f"Traceback: {traceback.format_exc()}")
        return None
```

## 5. Script de Test Complet

Un nouveau script `test_detection_complete.py` a été créé pour tester le cycle complet de détection :

```python
async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Test the complete detection process with AcoustID and AudD")
    parser.add_argument("audio_file", help="Path to the audio file to test")
    parser.add_argument("--acoustid", action="store_true", help="Test AcoustID detection")
    parser.add_argument("--audd", action="store_true", help="Test AudD detection")
    parser.add_argument("--verify", action="store_true", help="Verify track in database after detection")
    
    args = parser.parse_args()
    
    # ... (test de la détection avec AcoustID et AudD)
    
    # Vérifier la piste dans la base de données
    if args.verify:
        if acoustid_result and "track" in acoustid_result and "id" in acoustid_result["track"]:
            await verify_track_in_database(db_session, acoustid_result["track"]["id"])
        elif audd_result and "track" in audd_result and "id" in audd_result["track"]:
            await verify_track_in_database(db_session, audd_result["track"]["id"])
        else:
            logger.warning("No track ID available for verification")
```

## 6. Tests avec la Musique Sénégalaise

Des tests spécifiques ont été réalisés avec des échantillons de musique sénégalaise pour évaluer les performances du système de détection sur ce type de contenu.

### 6.1 Résultats des Tests

Les tests ont révélé plusieurs points importants :

1. **Détection avec AcoustID** :
   - La détection avec AcoustID échoue généralement pour la musique africaine
   - L'API répond correctement (statut 200) mais ne trouve pas de correspondance
   - Cela est probablement dû à une sous-représentation de la musique africaine dans la base de données AcoustID

2. **Détection avec AudD** :
   - AudD est beaucoup plus performant pour la détection de la musique africaine
   - Les tests ont montré une identification correcte de morceaux sénégalais comme "Dëgg La" par Pape Diouf
   - AudD fournit des métadonnées complètes incluant l'ISRC, le label, et la date de sortie

3. **Problèmes identifiés** :
   - Malgré une détection réussie par AudD, les métadonnées ne sont pas toujours correctement enregistrées dans la base de données
   - Les pistes sont parfois enregistrées comme "Unknown Track" par "Unknown Artist" malgré l'identification correcte
   - Les ISRC et labels ne sont pas systématiquement sauvegardés

### 6.2 Recommandations pour la Musique Africaine

Pour améliorer la détection de la musique africaine, les modifications suivantes sont recommandées :

1. **Prioritisation d'AudD** :
   - Pour les stations diffusant principalement de la musique africaine, configurer le système pour utiliser AudD en priorité
   - Créer un paramètre de configuration par station pour définir l'ordre de priorité des services de détection

2. **Base de données locale spécialisée** :
   - Développer une base de données locale d'empreintes digitales spécifique à la musique africaine
   - Mettre en place un processus d'enrichissement continu de cette base de données

3. **Correction de la mise à jour des métadonnées** :
   - Réviser la méthode `find_audd_match` pour garantir que les métadonnées sont correctement extraites et enregistrées
   - Ajouter des vérifications supplémentaires pour s'assurer que les métadonnées sont bien sauvegardées

4. **Logging amélioré** :
   - Implémenter un logging plus détaillé pour le processus de mise à jour des métadonnées
   - Créer des alertes spécifiques pour les cas où les métadonnées sont détectées mais non sauvegardées

### 6.3 Exemple de Détection Réussie

Voici un exemple de détection réussie par AudD pour un morceau sénégalais :

```
[AUDD] AudD found track: Dëgg La by Pape Diouf
[AUDD] ISRC found in Apple Music data: FR10S1455141
[AUDD] AudD detection result: Dëgg La by Pape Diouf
```

Ces informations devraient être correctement enregistrées dans la base de données, mais des problèmes ont été identifiés dans ce processus qui nécessitent des corrections.

## 7. Prochaines Étapes

Les prochaines améliorations prévues pour le système de détection sont :

1. **Correction des problèmes de métadonnées** :
   - Résoudre le problème de mise à jour des métadonnées identifié lors des tests avec la musique sénégalaise
   - Améliorer la gestion des caractères spéciaux dans les titres et noms d'artistes

2. **Optimisation des performances** :
   - Mise en place de mécanismes de cache pour les empreintes fréquemment utilisées
   - Optimisation des requêtes SQL pour améliorer les performances de recherche

3. **Amélioration de la recherche par similarité** :
   - Implémentation d'algorithmes de recherche plus avancés pour améliorer la précision de la détection
   - Utilisation de techniques d'indexation pour accélérer la recherche

4. **Intégration de Chromaprint** :
   - Utilisation de l'algorithme Chromaprint pour générer des empreintes plus robustes
   - Comparaison des performances entre les empreintes MD5 et Chromaprint

5. **Tests et validation** :
   - Création de tests unitaires pour valider les modifications
   - Mesure des performances et de la précision de la détection

## 8. Comment Tester les Améliorations

Pour tester les améliorations, utilisez le script `test_detection_complete.py` :

```bash
python test_detection_complete.py /chemin/vers/fichier/audio.mp3 --verify
```

Ce script testera la détection avec AcoustID et AudD, et vérifiera que les métadonnées sont correctement enregistrées dans la base de données. 