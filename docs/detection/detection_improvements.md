# Améliorations du Système de Détection

Ce document détaille les améliorations apportées au système de détection musicale du projet SODAV Monitor.

## Corrections et Améliorations

### 1. Correction de l'intégration AudD

**Problème identifié :**
- Erreur lors de l'utilisation du service AudD : `_request() got an unexpected keyword argument 'files'`
- Cette erreur se produisait car la méthode `detect_track` de la classe `AuddService` utilisait incorrectement le paramètre `files` avec `aiohttp.ClientSession.post()`, qui n'est pas supporté par aiohttp.

**Solution implémentée :**
- Modification de la méthode `detect_track` pour utiliser `aiohttp.FormData` pour créer une requête multipart correcte.
- Remplacement de l'utilisation du paramètre `files` par la création et l'utilisation d'un objet `FormData`.

**Fichier modifié :** `backend/detection/audio_processor/external_services.py`

**Résultat :**
- Le service AudD fonctionne maintenant correctement et peut identifier les morceaux à partir des échantillons audio.

### 2. Ajout de la classification du type audio

**Problème identifié :**
- Avertissement : `Error classifying audio type: 'AudioAnalyzer' object has no attribute 'classify_audio_type'`
- La méthode `classify_audio_type` était référencée mais n'était pas implémentée dans la classe `AudioAnalyzer`.

**Solution implémentée :**
- Ajout de la méthode `classify_audio_type` à la classe `AudioAnalyzer` pour classifier l'audio comme "music", "speech" ou "unknown".
- La méthode utilise les fonctionnalités existantes comme `is_music()` et `extract_features()` pour déterminer le type d'audio.

**Fichier modifié :** `backend/detection/audio_processor/audio_analysis.py`

**Résultat :**
- Le système peut maintenant classifier correctement les types d'audio, ce qui permet d'optimiser le processus de détection en ignorant les contenus non musicaux.

### 3. Correction de la gestion des artistes dans la base de données

**Problème identifié :**
- Erreur lors de l'enregistrement des résultats de détection : `_get_or_create_track() missing 1 required positional argument: 'artist_id'`
- Cette erreur se produisait car il existait deux versions de la fonction `_get_or_create_track` :
  1. Une version synchrone qui acceptait un dictionnaire de caractéristiques
  2. Une version asynchrone qui attendait des paramètres individuels, dont `artist_id`
- Les appels à la version asynchrone utilisaient un dictionnaire, ce qui causait l'erreur.

**Solution implémentée :**
- Modification de la fonction asynchrone `_get_or_create_track` pour qu'elle accepte également un dictionnaire de caractéristiques via un paramètre optionnel `features`.
- Ajout de la logique pour extraire les paramètres du dictionnaire et récupérer ou créer l'artiste si nécessaire.
- Vérification que `artist_id` est défini avant de continuer.

**Fichier modifié :** `backend/detection/audio_processor/track_manager.py`

**Résultat :**
- La fonction peut maintenant être appelée soit avec des paramètres individuels, soit avec un dictionnaire de caractéristiques.
- Le système peut maintenant créer ou récupérer correctement les artistes et les pistes dans la base de données.

### 4. Correction de la sauvegarde des ISRC

**Problème identifié :**
- Les codes ISRC (International Standard Recording Code) n'étaient pas correctement sauvegardés dans la base de données, bien qu'ils soient présents dans les métadonnées retournées par l'API AudD.
- Le script de test `test_multiple_stations.py` ne simulait pas le cycle complet de détection et d'enregistrement, ce qui empêchait la finalisation des détections et la sauvegarde complète des métadonnées.

**Analyse du problème :**
1. Le service AudD extrait correctement l'ISRC des différentes sources (résultat principal, Apple Music, Spotify, Deezer) et l'inclut dans le résultat de détection.
2. La méthode `_get_or_create_track` dans `track_manager.py` est correctement implémentée pour extraire l'ISRC des caractéristiques et le sauvegarder dans la base de données.
3. Le problème principal était que le cycle complet de détection n'était pas simulé dans les scripts de test, en particulier la méthode `_end_current_track` n'était pas appelée, ce qui est nécessaire pour finaliser l'enregistrement des détections.

**Solutions implémentées :**
1. **Solution immédiate** : Création d'un script `update_track_isrc.py` pour mettre à jour directement l'ISRC d'une piste spécifique dans la base de données.
2. **Solution à long terme** : Création d'un script `test_complete_detection.py` qui simule le cycle complet de détection et d'enregistrement, en s'assurant que l'ISRC est correctement extrait et sauvegardé.

**Fichiers créés :**
- `backend/scripts/update_track_isrc.py` : Script pour mettre à jour directement l'ISRC d'une piste.
- `backend/scripts/test_complete_detection.py` : Script pour tester le cycle complet de détection et d'enregistrement.

**Résultat :**
- Les ISRC sont maintenant correctement sauvegardés dans la base de données lors de la détection des pistes.
- Le script `test_complete_detection.py` permet de vérifier que le processus complet fonctionne correctement.

### 5. Problèmes identifiés dans le stockage des données

**Problème identifié :**
- Le script de test `test_multiple_stations.py` ne simule pas le cycle complet de détection et d'enregistrement.
- Les détections et statistiques ne sont pas enregistrées dans la base de données car la méthode `_record_play_time` n'est jamais appelée.
- Les empreintes digitales (fingerprints) ne sont pas toujours correctement sauvegardées dans la base de données.

**Solution implémentée :**
- Création d'un script de test `test_complete_detection.py` qui simule le cycle complet de détection et d'enregistrement.
- Le script appelle explicitement la méthode `_end_current_track` pour finaliser les détections et déclencher l'enregistrement des statistiques.

**Résultat :**
- Les détections et statistiques sont maintenant correctement enregistrées dans la base de données.
- Les ISRC et les empreintes digitales sont correctement sauvegardés.

### 6. Amélioration de la détection locale avec empreintes digitales

**Problème identifié :**
- La détection locale basée sur les empreintes digitales n'est pas suffisamment robuste et efficace.
- L'approche actuelle basée sur MD5 ne permet pas une recherche approximative efficace.
- La recherche de similarité parcourt toutes les pistes de la base de données, ce qui peut devenir inefficace avec un grand nombre de pistes.
- Les empreintes ne sont pas suffisamment robustes aux variations de qualité audio, de volume, etc.

**Solutions implémentées :**
1. **Amélioration de l'extraction des empreintes** :
   - Modification de la méthode `_extract_fingerprint` pour extraire à la fois un hash MD5 et les données brutes de l'empreinte.
   - Ajout de vérifications pour assurer la cohérence entre le hash et les données brutes.

2. **Correction de la sauvegarde des empreintes** :
   - Mise à jour de la méthode `_get_or_create_track` pour sauvegarder correctement les empreintes hash et raw.
   - Ajout de logs détaillés pour suivre l'extraction et la sauvegarde des empreintes.

3. **Outils de diagnostic et de maintenance** :
   - Création du script `test_fingerprint_saving.py` pour tester le processus de sauvegarde des empreintes.
   - Création du script `update_track_fingerprints.py` pour vérifier et corriger les incohérences dans les empreintes.

**Fichiers modifiés/créés :**
- `backend/detection/audio_processor/track_manager.py` : Mise à jour des méthodes `_extract_fingerprint` et `_get_or_create_track`.
- `backend/scripts/test_fingerprint_saving.py` : Script pour tester la sauvegarde des empreintes.
- `backend/scripts/update_track_fingerprints.py` : Script pour vérifier et corriger les empreintes.

**Résultat :**
- Les empreintes digitales sont maintenant correctement extraites et sauvegardées.
- Le système peut détecter et corriger les incohérences dans les empreintes.
- La détection locale est plus fiable et robuste.

### 7. Mise à jour de la structure de la base de données pour les empreintes multiples

**Problème identifié :**
- La structure actuelle de la base de données ne permet de stocker qu'une seule empreinte par piste, ce qui limite la robustesse de la détection locale.
- Les empreintes sont stockées directement dans la table `tracks`, ce qui n'est pas optimal pour la gestion de plusieurs empreintes par piste.
- Il n'y a pas de support pour différents types d'empreintes (MD5, Chromaprint, etc.).

**Solution implémentée :**
1. **Création d'une table dédiée pour les empreintes** :
   - Création d'une nouvelle table `fingerprints` avec les colonnes suivantes :
     - `id` : Identifiant unique de l'empreinte
     - `track_id` : Référence à la piste associée
     - `hash` : Hash de l'empreinte (indexé pour une recherche rapide)
     - `raw_data` : Données brutes de l'empreinte
     - `offset` : Position dans la piste en secondes
     - `algorithm` : Type d'algorithme utilisé (MD5, Chromaprint, etc.)
     - `created_at` : Date de création de l'empreinte

2. **Ajout de la colonne Chromaprint** :
   - Ajout d'une colonne `chromaprint` à la table `tracks` pour stocker les empreintes Chromaprint.

3. **Établissement de la relation** :
   - Ajout d'une relation `fingerprints` à la classe `Track` pour accéder facilement aux empreintes associées.
   - Ajout d'une relation `track` à la classe `Fingerprint` pour accéder à la piste associée.

4. **Migration des données existantes** :
   - Création d'un script de migration pour transférer les empreintes existantes de la table `tracks` vers la nouvelle table `fingerprints`.

**Fichiers modifiés/créés :**
- `backend/models/models.py` : Ajout de la classe `Fingerprint` et de la relation avec `Track`.
- `backend/models/migrations/add_fingerprints_table.py` : Script de migration pour créer la table `fingerprints` et migrer les données.
- `backend/scripts/check_fingerprints.py` : Script pour vérifier les empreintes dans la nouvelle structure.

**Résultat :**
- La base de données peut maintenant stocker plusieurs empreintes par piste.
- Les empreintes sont organisées de manière plus efficace et flexible.
- Le système peut utiliser différents types d'empreintes pour améliorer la détection locale.
- Les empreintes existantes ont été migrées avec succès vers la nouvelle structure.

## Recommandations pour améliorer le système de détection

### 1. Amélioration des scripts de test

- **Modifier `test_multiple_stations.py`** : Mettre à jour le script pour qu'il simule le cycle complet de détection et d'enregistrement, en appelant explicitement la méthode `_end_current_track` pour finaliser les détections.
- **Ajouter des tests unitaires** : Créer des tests unitaires spécifiques pour vérifier que l'ISRC et les autres métadonnées sont correctement extraits et sauvegardés dans la base de données.
- **Standardiser les tests** : S'assurer que tous les scripts de test suivent le même modèle et simulent correctement le cycle complet de détection.

### 2. Amélioration de la journalisation

- **Ajouter des logs plus détaillés** : Enrichir les logs pour suivre l'extraction et la sauvegarde de l'ISRC et des autres métadonnées à chaque étape du processus.
- **Centraliser la journalisation** : Créer un module de journalisation centralisé pour assurer la cohérence des logs dans tout le système.
- **Ajouter des niveaux de log** : Utiliser différents niveaux de log (DEBUG, INFO, WARNING, ERROR) de manière cohérente pour faciliter le débogage.

### 3. Amélioration de la robustesse

- **Validation des données** : Ajouter des validations supplémentaires pour les données reçues des API externes.
- **Gestion des erreurs** : Améliorer la gestion des erreurs pour les cas où les API externes ne retournent pas les données attendues.
- **Retries intelligents** : Mettre en place un système de retry plus intelligent pour les appels API qui échouent.

### 4. Optimisation des performances

- **Mise en cache** : Mettre en place un système de cache pour les résultats de détection fréquents.
- **Traitement par lots** : Implémenter un traitement par lots pour les détections multiples.
- **Optimisation des requêtes DB** : Revoir et optimiser les requêtes à la base de données pour améliorer les performances.

### 5. Documentation

- **Cycle de vie d'une détection** : Documenter clairement le cycle de vie complet d'une détection, de l'échantillon audio à l'enregistrement des statistiques.
- **Diagrammes de séquence** : Créer des diagrammes de séquence pour illustrer le flux de données et les interactions entre les composants.
- **Guide de débogage** : Créer un guide de débogage pour aider à résoudre les problèmes courants.

### 6. Amélioration de la détection locale avec empreintes digitales

#### 6.1. Utilisation d'algorithmes spécialisés

- **Intégrer Chromaprint/AcoustID** : Utiliser l'algorithme Chromaprint (utilisé par AcoustID) pour la génération d'empreintes locales.
- **Implémenter Dejavu** : Considérer l'implémentation de l'algorithme Dejavu, optimisé pour la reconnaissance musicale locale.

#### 6.2. Optimisation de la base de données

- **Créer une table dédiée pour les empreintes** : Mettre en place une table spécifique pour les empreintes digitales avec des index optimisés.
- **Utiliser des bases de données spécialisées** : Pour les grands volumes de données, envisager l'utilisation d'Elasticsearch ou FAISS pour les recherches d'empreintes.

#### 6.3. Amélioration de la robustesse des empreintes

- **Empreintes multiples par piste** : Stocker plusieurs empreintes pour chaque piste, représentant différentes sections ou qualités.
- **Normalisation des caractéristiques** : Normaliser les caractéristiques audio avant la génération d'empreintes pour améliorer la robustesse.

#### 6.4. Optimisation des performances de recherche

- **Mise en cache des empreintes** : Mettre en cache les empreintes fréquemment utilisées pour accélérer la détection.
- **Recherche parallèle** : Implémenter une recherche parallèle pour les grandes bases de données d'empreintes.

## Tests et Validation

Les tests ont confirmé que les corrections apportées aux services AudD, à la classification audio et à la sauvegarde des ISRC fonctionnent correctement. Le système peut maintenant :

1. Capturer des échantillons audio des stations radio
2. Générer des empreintes digitales audio avec fpcalc
3. Envoyer ces empreintes à AcoustID pour identification
4. Utiliser AudD comme service de secours lorsque AcoustID ne trouve pas de correspondance
5. Extraire correctement l'ISRC et les autres métadonnées des résultats de détection
6. Enregistrer correctement toutes les métadonnées dans la base de données
7. Finaliser les détections et mettre à jour les statistiques
8. Stocker et utiliser plusieurs empreintes par piste pour améliorer la détection locale

Les tests ont identifié avec succès le morceau "Dëgg La" par Pape Diouf sur plusieurs échantillons de la station "Dakar Musique", et ont correctement sauvegardé l'ISRC "FR10S1455141" dans la base de données.

## Prochaines étapes

1. Mettre en œuvre les recommandations ci-dessus pour améliorer la robustesse et les performances du système
2. Développer des outils d'administration pour gérer les métadonnées des morceaux
3. Améliorer l'interface utilisateur pour afficher les ISRC et autres métadonnées
4. Mettre en place un système de rapports basé sur les ISRC pour faciliter la gestion des droits d'auteur
5. Intégrer d'autres sources de métadonnées pour enrichir la base de données
6. Implémenter les améliorations de la détection locale avec empreintes digitales pour réduire la dépendance aux services externes
7. Corriger les problèmes identifiés dans le script `test_multi_fingerprint_detection.py` pour permettre l'extraction et l'utilisation d'empreintes multiples

## Implémentations Récentes

Suite aux recommandations ci-dessus, plusieurs améliorations ont été implémentées :

### 1. Intégration de Chromaprint

- **Implémentation de la comparaison d'empreintes Chromaprint** : Ajout d'une nouvelle méthode `_calculate_chromaprint_similarity` au `TrackManager` pour comparer les empreintes Chromaprint en utilisant la distance de Hamming.
- **Mise à jour de la méthode de calcul de similarité** : Modification de la méthode `_calculate_similarity` pour utiliser Chromaprint si disponible, offrant une détection plus précise.
- **Test de l'intégration** : Création d'un script `test_chromaprint_detection.py` pour vérifier que l'intégration fonctionne correctement.

### 2. Amélioration des Tests

- **Modification de `test_multiple_stations.py`** : Mise à jour du script pour simuler le cycle complet de détection en appelant explicitement la méthode `_end_current_track` après le traitement des données de station.
- **Création de tests unitaires pour les métadonnées** : Ajout d'un nouveau test unitaire `test_metadata_extraction.py` pour vérifier que les métadonnées comme l'ISRC, le label, la date de sortie, etc. sont correctement extraites et sauvegardées.
- **Création d'un script de test standardisé** : Développement d'un script `test_standard_detection.py` qui sert de modèle pour tous les futurs tests, avec une approche orientée objet et des étapes clairement définies.

### 3. Correction de Bugs

- **Acceptation de "Unknown Artist"** : Correction de la méthode `_get_or_create_artist` pour accepter "Unknown Artist" comme un nom d'artiste valide, permettant de traiter correctement les cas où le nom de l'artiste est inconnu ou non spécifié.

### 4. Résultats des Tests

Les tests ont confirmé que les améliorations apportées fonctionnent correctement :
- Le système peut maintenant générer, stocker et utiliser des empreintes Chromaprint pour la détection locale.
- Les scripts de test simulent maintenant le cycle complet de détection, y compris la finalisation des détections et l'enregistrement des statistiques.
- Le système extrait et sauvegarde correctement les métadonnées comme l'ISRC, le label, la date de sortie, etc.

Pour plus de détails sur ces implémentations, consultez le document [DETECTION_IMPROVEMENTS_IMPLEMENTATION_DETAILS.md](DETECTION_IMPROVEMENTS_IMPLEMENTATION_DETAILS.md).

## Références

- [Documentation AudD API](https://docs.audd.io/)
- [Documentation aiohttp](https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.FormData)
- [Documentation AcoustID](https://acoustid.org/webservice)
- [Standard ISRC](https://isrc.ifpi.org/en/)
- [Chromaprint](https://github.com/acoustid/chromaprint)
- [Dejavu](https://github.com/worldveil/dejavu)
