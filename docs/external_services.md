# Services Externes de Détection Musicale

Ce document explique comment les services externes de détection musicale (MusicBrainz, AcoustID et AudD) sont intégrés et utilisés dans le projet SODAV Monitor.

## Vue d'ensemble

SODAV Monitor utilise une approche hiérarchique pour la détection musicale :

1. **Détection locale** : Recherche dans la base de données locale à l'aide des empreintes digitales enregistrées.
2. **Détection MusicBrainz par métadonnées** : Si la détection locale échoue, recherche dans MusicBrainz en utilisant les métadonnées (artiste, titre).
3. **Détection AcoustID** : Si la détection par métadonnées échoue, tente une détection par empreinte digitale via AcoustID.
4. **Détection AudD** : Si AcoustID échoue, utilise l'API AudD comme solution de dernier recours.

## Améliorations récentes

### Capture d'informations supplémentaires
Le système capture désormais des informations supplémentaires pour chaque détection :
- ISRC (International Standard Recording Code)
- Label de l'artiste
- Date de sortie
- Temps de jeu exact
- Empreinte digitale (fingerprint)
- Genre musical

### Génération et stockage d'empreintes digitales
Le système génère et stocke des empreintes digitales pour les nouvelles détections, ce qui permet :
- De réduire la dépendance aux API externes
- D'améliorer la vitesse de détection
- D'augmenter la précision des détections futures

### Détection locale améliorée
La détection locale a été améliorée pour utiliser une correspondance exacte des empreintes digitales :
- Recherche d'abord une correspondance exacte de l'empreinte digitale
- Si aucune correspondance exacte n'est trouvée, utilise une comparaison de similarité
- Permet une détection plus rapide et plus précise des pistes déjà connues

### Réutilisation des empreintes digitales
Une nouvelle fonctionnalité permet de réutiliser les empreintes digitales stockées :
- Les empreintes digitales sont stockées dans la base de données lors de la première détection
- Lors des détections suivantes, le système recherche d'abord une correspondance exacte dans la base de données
- Cette approche réduit considérablement la dépendance aux API externes et améliore les performances

### Enregistrement du temps de jeu
Le système enregistre avec précision le temps de jeu des pistes détectées, ce qui est essentiel pour :
- Le calcul des redevances
- Les statistiques de diffusion

### Traçabilité des méthodes de détection
Le système enregistre désormais la méthode de détection utilisée pour chaque piste :
- "local" : Détection via la base de données locale
- "musicbrainz" : Détection via l'API MusicBrainz
- "acoustid" : Détection via l'API AcoustID
- "audd" : Détection via l'API AudD

## Configuration des clés API

Les clés API pour AcoustID et AudD doivent être configurées dans le fichier `.env` :

```
# APIs Externes
ACOUSTID_API_KEY=votre_clé_acoustid
AUDD_API_KEY=votre_clé_audd
```

### Obtention des clés API

- **AcoustID** : Obtenez une clé API gratuite sur [https://acoustid.org/api-key](https://acoustid.org/api-key)
- **AudD** : Inscrivez-vous sur [https://dashboard.audd.io/](https://dashboard.audd.io/) pour obtenir une clé API

### État actuel des clés API

Nos tests ont révélé des problèmes avec les clés API actuelles :

- **AcoustID** : La clé actuelle (`7HKKBoukZR`) génère une erreur 400 (Bad Request) lorsqu'elle est utilisée avec des données audio brutes. L'API AcoustID nécessite que les données audio soient prétraitées avec l'outil `fpcalc` pour générer une empreinte digitale.

- **AudD** : La clé actuelle (`a718282167d84385a8c9d1ea9f45747a`) fonctionne correctement lorsqu'elle est utilisée avec une URL d'exemple fournie par AudD (`https://audd.tech/example1.mp3`), mais génère une erreur "api_token is disabled" lorsqu'elle est utilisée avec des données audio brutes. Cela suggère que la clé est valide mais limitée ou désactivée pour certaines fonctionnalités.

### Solutions implémentées

Pour contourner ces problèmes, nous avons implémenté les solutions suivantes :

1. **Recherche par métadonnées avec MusicBrainz** : Nous avons ajouté une nouvelle méthode de détection qui utilise l'API MusicBrainz pour rechercher des pistes par artiste et titre, sans nécessiter d'empreinte digitale. Cette méthode est maintenant utilisée comme deuxième étape dans le processus de détection, avant d'essayer AcoustID.

2. **Détection par URL avec AudD** : Nous avons ajouté une méthode pour utiliser l'API AudD avec des URLs plutôt qu'avec des données audio brutes, ce qui fonctionne avec la clé API actuelle.

3. **Installation locale de fpcalc** : Nous avons intégré l'outil fpcalc directement dans le projet pour permettre la génération d'empreintes digitales sans dépendre d'une installation externe.

4. **Stockage des empreintes digitales** : Nous stockons désormais les empreintes digitales dans la base de données pour permettre une détection locale plus efficace.

## Installation et configuration de fpcalc

### À propos de fpcalc

`fpcalc` est un outil en ligne de commande qui génère des empreintes digitales audio pour le service AcoustID. Il est nécessaire pour utiliser l'API AcoustID avec des données audio brutes.

### Installation intégrée

Pour simplifier le déploiement et éviter les problèmes de compatibilité, nous avons intégré fpcalc directement dans le projet :

1. L'exécutable fpcalc est stocké dans le dossier `backend/bin/`
2. Le système détecte automatiquement cet exécutable et l'utilise pour la génération d'empreintes digitales
3. Aucune installation supplémentaire n'est nécessaire

### Vérification de l'installation

Pour vérifier que fpcalc est correctement installé et fonctionne, vous pouvez exécuter le script de test suivant :

```bash
python backend/scripts/detection/external_services/test_acoustid_fpcalc.py
```

Ce script teste la génération d'empreintes digitales avec fpcalc et affiche les résultats.

### Installation manuelle (si nécessaire)

Si vous souhaitez utiliser une version différente de fpcalc, vous pouvez l'installer manuellement :

1. Téléchargez fpcalc depuis [https://acoustid.org/chromaprint](https://acoustid.org/chromaprint)
2. Extrayez l'exécutable fpcalc
3. Placez-le dans le dossier `backend/bin/` du projet
4. Assurez-vous qu'il est exécutable (`chmod +x backend/bin/fpcalc` sur Linux/Mac)

## Implémentation

### MusicBrainz

Le service MusicBrainz est implémenté dans la classe `AcoustIDService` (pour des raisons de compatibilité) dans `backend/detection/audio_processor/external_services.py`. Cette classe fournit des méthodes pour :

- Rechercher des pistes par métadonnées (artiste, titre)
- Analyser les résultats de l'API
- Extraire les informations pertinentes sur les pistes (ISRC, label, date de sortie)

```python
from detection.audio_processor.external_services import AcoustIDService

# Initialiser le service
acoustid_service = AcoustIDService(api_key=os.environ.get("ACOUSTID_API_KEY"))

# Rechercher une piste par métadonnées
result = await acoustid_service.search_by_metadata(artist="Michael Jackson", title="Thriller")
```

### AcoustID

Le service AcoustID est également implémenté dans la classe `AcoustIDService` dans `backend/detection/audio_processor/external_services.py`. Cette classe fournit des méthodes pour :

- Générer des empreintes digitales avec fpcalc
- Envoyer des empreintes digitales à l'API AcoustID
- Analyser les résultats de l'API
- Extraire les informations pertinentes sur les pistes (ISRC, label, date de sortie)

```python
from detection.audio_processor.external_services import AcoustIDService

# Initialiser le service
acoustid_service = AcoustIDService(api_key=os.environ.get("ACOUSTID_API_KEY"))

# Détecter une piste avec des données audio brutes
result = await acoustid_service.detect_track(audio_data)
```

### AudD

Le service AudD est implémenté dans la classe `AuddService` dans `backend/detection/audio_processor/external_services.py`. Cette classe fournit des méthodes pour :

- Envoyer des données audio à l'API AudD
- Envoyer des URLs à l'API AudD
- Analyser les résultats de l'API
- Extraire les informations pertinentes sur les pistes (ISRC, label, date de sortie)

```python
from detection.audio_processor.external_services import AuddService

# Initialiser le service
audd_service = AuddService(api_key=os.environ.get("AUDD_API_KEY"))

# Détecter une piste avec des données audio brutes
result = await audd_service.detect_track(audio_data)

# Détecter une piste avec une URL
result = await audd_service.detect_track_with_url(url)
```

## Gestionnaire de services externes

La classe `ExternalServiceHandler` dans `backend/detection/audio_processor/external_services.py` fournit une interface unifiée pour tous les services externes. Elle :

- Initialise les services avec les clés API appropriées
- Gère les erreurs et les retries
- Fournit des méthodes pour reconnaître la musique avec chaque service

```python
from detection.audio_processor.external_services import ExternalServiceHandler

# Initialiser le gestionnaire
handler = ExternalServiceHandler(db_session)

# Reconnaître avec MusicBrainz par métadonnées
musicbrainz_result = await handler.recognize_with_musicbrainz_metadata(artist, title)

# Reconnaître avec AcoustID
acoustid_result = await handler.recognize_with_acoustid(audio_data)

# Reconnaître avec AudD (données audio brutes)
audd_result = await handler.recognize_with_audd(audio_data)

# Reconnaître avec AudD (URL)
audd_result = await handler.recognize_with_audd_url(url)
```

## Intégration dans le processus de détection

Les services externes sont intégrés dans le processus de détection via la classe `TrackManager` dans `backend/detection/audio_processor/track_manager.py`. Cette classe :

- Tente d'abord une détection locale
- Si la détection locale échoue, tente une détection avec MusicBrainz par métadonnées
- Si la détection par métadonnées échoue, tente une détection avec AcoustID
- Si AcoustID échoue, tente une détection avec AudD
- Enregistre les résultats dans la base de données, y compris :
  - ISRC
  - Label
  - Date de sortie
  - Temps de jeu exact
  - Empreinte digitale

## Processus de détection hiérarchique

Le processus de détection hiérarchique est implémenté dans la méthode `process_stream` de la classe `AudioProcessor` dans `backend/detection/audio_processor/core.py`. Cette méthode :

1. Extrait les caractéristiques audio du segment audio
2. Détermine si le segment contient de la musique ou de la parole
3. Si c'est de la musique, tente une détection locale
4. Si la détection locale échoue, tente une détection avec MusicBrainz par métadonnées
5. Si la détection par métadonnées échoue, tente une détection avec AcoustID
6. Si AcoustID échoue, tente une détection avec AudD
7. Si toutes les méthodes échouent, retourne un résultat avec source "unknown"

## Enregistrement des données de détection

Pour chaque détection réussie, le système enregistre les informations suivantes :

1. **Informations de base** :
   - Titre de la piste
   - Artiste
   - Album

2. **Informations supplémentaires** :
   - ISRC
   - Label
   - Date de sortie
   - Empreinte digitale

3. **Données de diffusion** :
   - Station de radio
   - Heure de détection
   - Durée de diffusion
   - Méthode de détection utilisée
   - Niveau de confiance

Ces informations sont stockées dans plusieurs tables :
- `tracks` : Informations sur les pistes
- `track_detections` : Détections individuelles
- `station_track_stats` : Statistiques de diffusion par station et par piste

## Test des services externes

Des scripts de test sont disponibles pour vérifier que les services externes fonctionnent correctement :

```bash
# Test de la recherche par métadonnées avec MusicBrainz
python backend/scripts/detection/external_services/test_musicbrainz_simple.py

# Test de l'API AudD avec URL
python backend/scripts/detection/external_services/test_audd_url_simple.py

# Test de fpcalc et AcoustID
python backend/scripts/detection/external_services/test_acoustid_fpcalc.py

# Test complet du processus de détection hiérarchique
python backend/scripts/detection/test_detection_hierarchy.py

# Test spécifique de la détection AudD
python backend/scripts/detection/test_audd_detection.py
```

Ces scripts testent les différents services avec différentes approches et affichent les résultats.

## Dépannage

### fpcalc

- **Problème** : fpcalc n'est pas exécutable
  - **Solution** : Vérifiez les permissions avec `chmod +x backend/bin/fpcalc`

- **Problème** : fpcalc génère une erreur "Bad CPU type in executable"
  - **Solution** : Téléchargez la version de fpcalc correspondant à votre architecture (Intel ou Apple Silicon)

- **Problème** : fpcalc n'est pas trouvé
  - **Solution** : Vérifiez que le fichier existe dans `backend/bin/` ou installez-le manuellement

### MusicBrainz

- Assurez-vous que la clé API AcoustID est valide et correctement configurée dans le fichier `.env` (utilisée pour l'authentification)
- Vérifiez que les métadonnées (artiste, titre) sont correctes et suffisamment précises
- Consultez les logs pour les erreurs spécifiques à MusicBrainz
- Problèmes courants :
  - Erreur 503 : Service temporairement indisponible (rate limit atteint)
  - Erreur 400 : Requête mal formée
  - Aucun résultat trouvé : Les métadonnées ne correspondent à aucune piste dans la base de données

### AcoustID

- Assurez-vous que la clé API AcoustID est valide et correctement configurée dans le fichier `.env`
- Vérifiez que fpcalc est correctement installé et fonctionne
- Vérifiez que le format audio est compatible (MP3, WAV, FLAC)
- Consultez les logs pour les erreurs spécifiques à AcoustID
- Problèmes courants :
  - Erreur 400 : Format de requête incorrect ou clé API invalide
  - Erreur 401 : Clé API non autorisée
  - Erreur 429 : Trop de requêtes (rate limit atteint)

### AudD

- Assurez-vous que la clé API AudD est valide et correctement configurée dans le fichier `.env`
- Vérifiez que le format audio est compatible (MP3, WAV)
- Consultez les logs pour les erreurs spécifiques à AudD
- Problèmes courants :
  - Erreur "api_token is disabled" : La clé API a été désactivée pour certaines fonctionnalités, essayez d'utiliser l'API avec des URLs
  - Erreur "Recognition failed" : Le fichier audio n'a pas pu être reconnu
  - Erreur "Invalid api_token" : La clé API est invalide
  - Erreur "no valid audio URL" : L'URL fournie n'est pas accessible ou ne contient pas d'audio valide

## Limitations

- Les services externes nécessitent une connexion Internet
- Les API ont des limites de requêtes (rate limits)
- La qualité de la détection dépend de la qualité de l'audio
- Certaines pistes peuvent ne pas être reconnues si elles ne sont pas dans les bases de données des services
- L'utilisation de l'API AudD avec des URLs nécessite que les fichiers audio soient accessibles publiquement

## Recommandations pour améliorer la détection

1. **Améliorer la détection locale** :
   - Enrichir la base de données locale avec des empreintes digitales de pistes fréquemment diffusées
   - Optimiser l'algorithme de correspondance des empreintes

2. **Optimiser l'utilisation des API externes** :
   - Mettre en cache les résultats pour éviter des appels API répétés
   - Implémenter une stratégie de backoff exponentiel pour les retries
   - Surveiller l'utilisation des API pour éviter de dépasser les limites

3. **Considérer des alternatives** :
   - Explorer d'autres services de détection musicale comme Shazam API ou ACRCloud
   - Développer un système de détection propriétaire basé sur l'apprentissage automatique
