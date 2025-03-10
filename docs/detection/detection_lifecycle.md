# Cycle de Vie d'une Détection Musicale

Ce document détaille le cycle de vie complet d'une détection musicale dans le système SODAV Monitor, de l'échantillon audio à l'enregistrement des statistiques, en mettant l'accent sur la gestion des ISRC et autres métadonnées.

## 1. Vue d'ensemble du processus

Le processus de détection musicale se déroule en plusieurs étapes :

1. **Capture d'échantillon audio** : Un échantillon audio est capturé à partir d'une station radio.
2. **Analyse préliminaire** : L'échantillon est analysé pour déterminer s'il contient de la musique ou de la parole.
3. **Détection locale** : Le système tente d'abord de trouver une correspondance dans la base de données locale.
4. **Détection externe** : Si aucune correspondance locale n'est trouvée, le système utilise des services externes (AcoustID, puis AudD).
5. **Extraction des métadonnées** : Les métadonnées, y compris l'ISRC, sont extraites des résultats de détection.
6. **Création ou mise à jour de la piste** : La piste est créée ou mise à jour dans la base de données avec toutes les métadonnées.
7. **Suivi de la lecture** : Le système commence à suivre la lecture de la piste.
8. **Finalisation de la détection** : Lorsque la piste n'est plus détectée, la détection est finalisée.
9. **Enregistrement des statistiques** : Les statistiques de lecture sont enregistrées dans la base de données.

## 2. Détail des étapes clés

### 2.1. Capture d'échantillon audio

- **Méthode** : `capture_audio_sample()` dans `StationMonitor`
- **Description** : Capture un échantillon audio d'une durée spécifiée à partir d'une URL de flux radio.
- **Résultat** : Données audio brutes (bytes) prêtes à être analysées.

### 2.2. Analyse préliminaire

- **Méthode** : `classify_audio_type()` dans `AudioAnalyzer`
- **Description** : Analyse l'échantillon audio pour déterminer s'il contient de la musique ou de la parole.
- **Résultat** : Classification de l'audio comme "music", "speech" ou "unknown".
- **Importance** : Permet d'éviter de traiter des échantillons non musicaux, optimisant ainsi les ressources.

### 2.3. Détection locale

- **Méthode** : `find_local_match()` dans `TrackManager`
- **Description** : Recherche une correspondance dans la base de données locale en utilisant les empreintes digitales.
- **Processus détaillé** :
  1. Extraction de l'empreinte digitale à partir des caractéristiques audio
  2. Recherche d'une correspondance exacte dans la base de données
  3. Si aucune correspondance exacte n'est trouvée, calcul de la similarité avec toutes les pistes existantes
  4. Retour de la meilleure correspondance si le score de similarité dépasse un seuil (0.7)
- **Résultat** : Piste correspondante ou None si aucune correspondance n'est trouvée.

### 2.4. Détection externe

- **Méthodes** : 
  - `find_acoustid_match()` dans `TrackManager`
  - `find_audd_match()` dans `TrackManager`
- **Description** : Si aucune correspondance locale n'est trouvée, le système utilise d'abord AcoustID, puis AudD comme service de secours.
- **Résultat** : Métadonnées de la piste détectée, y compris l'ISRC si disponible.

### 2.5. Extraction des métadonnées

- **Méthode** : `detect_track()` dans `AuddService`
- **Description** : Extrait les métadonnées, y compris l'ISRC, des résultats de détection.
- **Détail de l'extraction de l'ISRC** : 
  1. Vérifie d'abord si l'ISRC est présent dans le résultat principal.
  2. Si non, vérifie dans les données Apple Music.
  3. Si non, vérifie dans les données Spotify.
  4. Si non, vérifie dans les données Deezer.
- **Résultat** : Dictionnaire contenant toutes les métadonnées de la piste, y compris l'ISRC.

### 2.6. Création ou mise à jour de la piste

- **Méthode** : `_get_or_create_track()` dans `TrackManager`
- **Description** : Crée une nouvelle piste ou met à jour une piste existante avec les métadonnées extraites.
- **Détail de la sauvegarde de l'ISRC** :
  1. Extrait l'ISRC des caractéristiques fournies.
  2. Si l'ISRC n'est pas directement disponible, vérifie dans les données Apple Music, Spotify et Deezer.
  3. Utilise l'ISRC comme critère de recherche pour trouver une piste existante.
  4. Si une piste est trouvée mais n'a pas d'ISRC, met à jour la piste avec l'ISRC trouvé.
  5. Si une nouvelle piste est créée, inclut l'ISRC dans les métadonnées.
- **Résultat** : Objet Track créé ou mis à jour dans la base de données.

### 2.7. Suivi de la lecture

- **Méthode** : `_start_track_detection()` dans `TrackManager`
- **Description** : Commence à suivre la lecture de la piste sur une station spécifique.
- **Résultat** : Enregistrement de la détection en cours avec l'heure de début.

### 2.8. Finalisation de la détection

- **Méthode** : `_end_current_track()` dans `TrackManager`
- **Description** : Finalise la détection lorsque la piste n'est plus détectée ou qu'une nouvelle piste est détectée.
- **Importance** : Cette étape est cruciale pour déclencher l'enregistrement des statistiques.
- **Résultat** : Calcul de la durée de lecture et préparation pour l'enregistrement des statistiques.

### 2.9. Enregistrement des statistiques

- **Méthode** : `_record_play_time()` dans `TrackManager`
- **Description** : Enregistre la détection et met à jour les statistiques dans la base de données.
- **Tables mises à jour** :
  - `track_detections` : Enregistre chaque détection individuelle.
  - `station_track_stats` : Met à jour les statistiques par station et par piste.
  - `track_stats` : Met à jour les statistiques globales par piste.
  - `artist_stats` : Met à jour les statistiques par artiste.
- **Résultat** : Statistiques complètes et à jour dans la base de données.

## 3. Détection locale avec empreintes digitales

### 3.1. Génération des empreintes digitales

- **Méthode** : `_extract_fingerprint()` dans `TrackManager`
- **Description** : Génère une empreinte digitale à partir des caractéristiques audio extraites.
- **Processus détaillé** :
  1. Vérification si une empreinte existe déjà dans les caractéristiques
  2. Si oui, utilisation de l'empreinte existante
  3. Si non, extraction des caractéristiques pertinentes (MFCC, chroma, centroïde spectral)
  4. Conversion en chaîne JSON et calcul d'un hash MD5
  5. Retour du hash (pour la recherche) et des données brutes (pour la comparaison)
- **Résultat** : Tuple contenant l'empreinte hash et les données brutes.

### 3.2. Stockage des empreintes digitales

- **Modèle** : Classe `Track` dans `models.py`
- **Champs** :
  - `fingerprint` : Empreinte digitale sous forme de chaîne hexadécimale (hash MD5)
  - `fingerprint_raw` : Données brutes de l'empreinte (stockées en BLOB)
- **Importance** : Les empreintes sont essentielles pour la détection locale et permettent de réduire la dépendance aux services externes.

### 3.3. Recherche par empreinte digitale

- **Méthode** : `find_local_match()` dans `TrackManager`
- **Processus de recherche** :
  1. **Correspondance exacte** : Recherche d'une piste avec exactement la même empreinte hash
  2. **Correspondance approximative** : Si aucune correspondance exacte n'est trouvée, calcul de la similarité avec toutes les pistes
  3. **Sélection** : Retour de la piste avec le score de similarité le plus élevé, si supérieur au seuil (0.7)
- **Calcul de similarité** :
  - **Méthode** : `_calculate_similarity()` dans `TrackManager`
  - **Caractéristiques utilisées** : MFCC, chroma, centroïde spectral, force rythmique
  - **Algorithme** : Calcul de la différence normalisée entre les vecteurs de caractéristiques

### 3.4. Avantages de la détection locale

1. **Autonomie** : Fonctionne sans connexion Internet
2. **Rapidité** : Plus rapide que les appels API externes
3. **Économie** : Réduit les coûts liés aux API externes
4. **Personnalisation** : Permet d'ajuster les algorithmes selon les besoins spécifiques
5. **Confidentialité** : Les données restent dans le système local

### 3.5. Limitations actuelles

1. **Performance** : La recherche de similarité parcourt toutes les pistes, ce qui peut devenir inefficace avec un grand nombre de pistes
2. **Précision** : L'approche actuelle basée sur MD5 ne permet pas une recherche approximative efficace
3. **Robustesse** : Les empreintes ne sont pas suffisamment robustes aux variations de qualité audio
4. **Indexation** : Absence d'indexation optimisée pour les recherches d'empreintes

### 3.6. Améliorations recommandées

1. **Algorithmes spécialisés** : Intégrer des algorithmes comme Chromaprint ou Dejavu
2. **Indexation optimisée** : Créer une table dédiée pour les empreintes avec des index appropriés
3. **Empreintes multiples** : Stocker plusieurs empreintes par piste pour améliorer la robustesse
4. **Normalisation** : Normaliser les caractéristiques audio avant la génération d'empreintes
5. **Mise en cache** : Mettre en cache les résultats de recherche fréquents
6. **Recherche parallèle** : Implémenter une recherche parallèle pour les grandes bases de données

## 4. Gestion des ISRC

### 4.1. Importance des ISRC

L'ISRC (International Standard Recording Code) est un identifiant unique pour les enregistrements sonores. Il est essentiel pour :
- L'identification précise des pistes dans les systèmes de gestion des droits d'auteur.
- La déduplication des pistes dans la base de données.
- La génération de rapports précis pour les sociétés de gestion collective.

### 4.2. Sources des ISRC

Les ISRC peuvent être obtenus à partir de plusieurs sources :
1. **Résultat principal d'AudD** : Parfois présent directement dans le résultat principal.
2. **Apple Music** : Souvent présent dans les métadonnées Apple Music.
3. **Spotify** : Présent dans les `external_ids` des métadonnées Spotify.
4. **Deezer** : Souvent présent directement dans les métadonnées Deezer.

### 4.3. Bonnes pratiques pour la sauvegarde des ISRC

1. **Extraction complète** : Vérifier toutes les sources possibles pour l'ISRC.
2. **Journalisation** : Enregistrer des logs détaillés pour suivre l'extraction et la sauvegarde des ISRC.
3. **Mise à jour des pistes existantes** : Si une piste existe déjà mais n'a pas d'ISRC, la mettre à jour avec l'ISRC trouvé.
4. **Validation** : Valider le format de l'ISRC avant de le sauvegarder (généralement 12 caractères, commençant par un code pays).
5. **Déduplication** : Utiliser l'ISRC comme critère de recherche pour éviter les doublons.

## 5. Problèmes courants et solutions

### 5.1. ISRC non sauvegardé

**Problème** : L'ISRC est présent dans les métadonnées mais n'est pas sauvegardé dans la base de données.

**Causes possibles** :
1. Le cycle de détection n'est pas complet (la méthode `_end_current_track()` n'est pas appelée).
2. L'extraction de l'ISRC échoue à trouver l'ISRC dans les métadonnées.
3. La mise à jour de la base de données échoue.

**Solutions** :
1. S'assurer que le cycle complet de détection est simulé dans les tests.
2. Ajouter des logs détaillés pour suivre l'extraction de l'ISRC.
3. Vérifier les transactions de base de données et les commits.

### 5.2. Gestion des durées et types de données

**Problème** : Les durées (duration) doivent être stockées sous forme d'objets `timedelta` dans la base de données PostgreSQL (type `interval`), mais sont parfois fournies sous forme d'entiers ou de flottants.

**Causes possibles** :
1. Les API externes retournent des durées en secondes (entiers ou flottants).
2. Les calculs internes produisent des durées en secondes.
3. Les conversions de type ne sont pas effectuées avant l'insertion en base de données.

**Solutions** :
1. **Conversion systématique** : Convertir toutes les durées en objets `timedelta` avant de les assigner aux modèles :
   ```python
   # Convertir la durée en timedelta si c'est un entier ou un float
   duration_value = track_info.get("duration", 0)
   if isinstance(duration_value, (int, float)):
       duration_value = timedelta(seconds=duration_value)
   
   track = Track(
       title=track_title,
       artist_id=artist.id,
       album=track_info.get("album", "Unknown Album"),
       duration=duration_value,
       fingerprint=track_info.get("fingerprint", "")
   )
   ```

2. **Validation dans les modèles** : Ajouter des méthodes de validation dans les modèles SQLAlchemy pour convertir automatiquement les durées :
   ```python
   @validates('duration')
   def validate_duration(self, key, value):
       if isinstance(value, (int, float)):
           return timedelta(seconds=value)
       return value
   ```

3. **Schémas Pydantic** : Utiliser des schémas Pydantic pour valider et convertir les données avant de les insérer dans la base de données :
   ```python
   class TrackCreate(BaseModel):
       title: str
       artist_id: int
       duration: Union[int, float, timedelta]
       
       @validator('duration')
       def validate_duration(cls, v):
           if isinstance(v, (int, float)):
               return timedelta(seconds=v)
           return v
   ```

4. **Tests spécifiques** : Ajouter des tests unitaires pour vérifier que les conversions de durée fonctionnent correctement.

### 5.3. Détections non finalisées

**Problème** : Les détections ne sont pas finalisées, ce qui empêche l'enregistrement des statistiques.

**Causes possibles** :
1. La méthode `_end_current_track()` n'est pas appelée.
2. Une exception interrompt le processus avant la finalisation.

**Solutions** :
1. Ajouter des mécanismes pour finaliser automatiquement les détections après un certain temps.
2. Améliorer la gestion des exceptions pour s'assurer que les détections sont toujours finalisées.

### 5.4. Doublons de pistes

**Problème** : Des pistes en double sont créées dans la base de données malgré des ISRC identiques.

**Causes possibles** :
1. L'ISRC n'est pas utilisé comme critère de recherche.
2. Des variations dans les titres ou les noms d'artistes empêchent la correspondance.

**Solutions** :
1. Utiliser l'ISRC comme critère principal de recherche.
2. Mettre en place des algorithmes de correspondance floue pour les titres et les noms d'artistes.

### 5.5. Problèmes avec les empreintes digitales

**Problème** : Les empreintes digitales ne permettent pas une détection locale fiable.

**Causes possibles** :
1. Algorithme de génération d'empreintes trop simple ou inadapté.
2. Variations dans la qualité audio ou le volume.
3. Incohérences entre les empreintes hash et les données brutes.

**Solutions** :
1. Utiliser des algorithmes spécialisés comme Chromaprint.
2. Normaliser les caractéristiques audio avant la génération d'empreintes.
3. Mettre en place des vérifications de cohérence entre hash et données brutes.
4. Utiliser le script `update_track_fingerprints.py` pour corriger les incohérences.

## 6. Tests et validation

### 6.1. Test du cycle complet

Pour tester correctement le cycle complet de détection et la sauvegarde des ISRC, utilisez le script `test_complete_detection.py` qui :
1. Simule la détection d'une piste avec AudD.
2. Extrait l'ISRC et autres métadonnées.
3. Crée ou met à jour la piste dans la base de données.
4. Simule le suivi de la lecture.
5. Finalise la détection.
6. Vérifie que l'ISRC et les statistiques sont correctement sauvegardés.

### 6.2. Test des empreintes digitales

Pour tester la génération et la sauvegarde des empreintes digitales, utilisez le script `test_fingerprint_saving.py` qui :
1. Détecte une piste à partir d'un fichier audio.
2. Génère une empreinte digitale à partir des données de détection.
3. Sauvegarde l'empreinte dans la base de données.
4. Vérifie la cohérence entre l'empreinte hash et les données brutes.

### 6.3. Test de la détection locale

Pour tester la détection locale avec les empreintes digitales, utilisez le script `test_local_detection.py` qui :
1. Crée une piste de test avec une empreinte digitale.
2. Simule une détection avec la même empreinte.
3. Vérifie que la piste est correctement identifiée via la détection locale.

### 6.4. Vérification et mise à jour des empreintes

Pour vérifier et mettre à jour les empreintes digitales existantes, utilisez le script `update_track_fingerprints.py` qui :
1. Vérifie la cohérence entre les empreintes hash et les données brutes.
2. Identifie les pistes avec des problèmes d'empreintes.
3. Met à jour les empreintes si nécessaire.

## 7. Conclusion

La gestion correcte du cycle de vie d'une détection, la sauvegarde des ISRC et l'utilisation efficace des empreintes digitales sont essentielles pour le bon fonctionnement du système SODAV Monitor. En suivant les bonnes pratiques décrites dans ce document, vous pouvez vous assurer que toutes les métadonnées sont correctement extraites et sauvegardées, et que la détection locale fonctionne de manière optimale, permettant ainsi une gestion précise des droits d'auteur et la génération de rapports fiables. 