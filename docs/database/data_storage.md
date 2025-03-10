# Stockage des Données dans SODAV Monitor

Ce document détaille comment les informations critiques sont stockées dans le système SODAV Monitor, en particulier les codes ISRC, les labels, les empreintes digitales (fingerprints) et les temps de lecture exacts.

## Codes ISRC

Les codes ISRC (International Standard Recording Code) sont des identifiants uniques pour les enregistrements sonores.

### Stockage
- Les codes ISRC sont stockés dans la table `tracks` dans la colonne `isrc` (type String(12))
- La colonne est indexée pour permettre des recherches rapides (`ix_tracks_isrc`)
- Une contrainte d'unicité est appliquée sur cette colonne pour éviter les doublons
- Le code ISRC est extrait des métadonnées fournies par les services de reconnaissance (AcoustID, Audd)

### Processus de sauvegarde
1. Lors de la détection d'une piste, si un code ISRC est présent dans les métadonnées retournées, il est extrait
2. Le système vérifie d'abord si une piste avec le même ISRC existe déjà dans la base de données
3. Si une piste avec le même ISRC existe :
   - Les statistiques de lecture sont mises à jour pour cette piste existante
   - Aucune nouvelle piste n'est créée, évitant ainsi les doublons
   - La confiance de détection est fixée à 1.0 (confiance maximale) pour les correspondances ISRC
4. Si aucune piste avec cet ISRC n'existe :
   - Dans la méthode `_get_or_create_track`, le code ISRC est utilisé comme critère de recherche pour trouver une piste existante
   - Si une piste est trouvée mais n'a pas de code ISRC, celui-ci est ajouté à la piste existante
   - Si une nouvelle piste est créée, le code ISRC est enregistré avec les autres métadonnées

### Importance de l'ISRC
- **Identifiant standard de l'industrie** : L'ISRC est un standard international reconnu par l'industrie musicale
- **Unicité garantie** : La contrainte d'unicité dans la base de données assure qu'un même code ISRC ne peut pas être associé à plusieurs pistes
- **Consolidation des statistiques** : Cette approche permet de consolider toutes les statistiques de lecture pour une même piste, même si elle est détectée par différentes méthodes
- **Réduction des faux positifs** : L'utilisation de l'ISRC comme identifiant principal réduit les faux positifs dans le processus de détection
- **Amélioration de la précision des rapports** : Les rapports générés sont plus précis car ils reflètent correctement le nombre réel de diffusions par piste
- **Optimisation des performances** : L'index sur la colonne ISRC permet des recherches rapides, améliorant les performances du système

### Implémentation technique
- La contrainte d'unicité a été ajoutée via une migration Alembic (`20250303_025434_add_isrc_unique_constraint.py`)
- Les méthodes `find_acoustid_match` et `find_audd_match` ont été modifiées pour vérifier d'abord l'existence d'une piste avec le même ISRC
- Le format de retour de ces méthodes a été standardisé pour inclure les informations complètes de la piste et un niveau de confiance élevé pour les correspondances ISRC

### Tests de validation
Des tests spécifiques ont été créés pour valider le bon fonctionnement de la contrainte d'unicité ISRC :
- Test de la contrainte d'unicité au niveau de la base de données
- Test de la recherche de pistes par ISRC
- Test de la détection avec AcoustID utilisant l'ISRC
- Test de la détection avec AudD utilisant l'ISRC
- Test de la mise à jour des statistiques de lecture pour les pistes existantes

## Labels

Les labels représentent les maisons de disques ou les éditeurs des pistes.

### Stockage
- Les labels sont stockés dans la table `tracks` dans la colonne `label` (type String)
- Les labels sont également stockés au niveau des artistes dans la table `artists` (colonne `label`)

### Processus de sauvegarde
1. Lors de la détection d'une piste, si un label est présent dans les métadonnées, il est extrait
2. Dans la méthode `_get_or_create_track`, si une piste existante est trouvée sans label, le label est ajouté
3. Si une nouvelle piste est créée, le label est enregistré avec les autres métadonnées

## Empreintes Digitales (Fingerprints)

Les empreintes digitales sont des représentations uniques du contenu audio permettant l'identification des pistes.

### Stockage
- Les empreintes sont stockées dans deux colonnes de la table `tracks`:
  - `fingerprint`: Version hachée de l'empreinte (type String, unique)
  - `fingerprint_raw`: Données binaires brutes de l'empreinte (type LargeBinary)
- Les empreintes sont également stockées dans la table `track_detections` pour chaque détection

### Processus de génération et sauvegarde
1. La méthode `_extract_fingerprint` génère une empreinte à partir des caractéristiques audio:
   - Utilise les caractéristiques MFCC, chroma et centroïde spectral si disponibles
   - Convertit ces données en chaîne JSON et calcule un hash MD5
2. L'empreinte est stockée avec la piste lors de sa création
3. Chaque détection stocke également l'empreinte utilisée pour l'identification

## Temps de Lecture Exact

Le système enregistre avec précision la durée de lecture de chaque piste sur chaque station.

### Stockage
- Le temps de lecture est stocké à plusieurs niveaux:
  1. **Détection individuelle**: Dans la table `track_detections`, colonne `play_duration` (type Interval)
  2. **Statistiques par station et piste**: Dans la table `station_track_stats`, colonne `total_play_time` (type Interval)
  3. **Statistiques globales par piste**: Dans la table `track_stats`, colonne `total_play_time` (type Interval)
  4. **Statistiques par artiste**: Dans la table `artist_stats`, colonne `total_play_time` (type Interval)
  5. **Statistiques quotidiennes et mensuelles**: Dans les tables `artist_daily` et `artist_monthly`

### Processus d'enregistrement
1. Lors de la détection d'une piste, la durée de lecture est calculée et enregistrée dans `track_detections`
2. La méthode `_record_play_time` enregistre cette durée et met à jour les statistiques
3. La méthode `_update_station_track_stats` met à jour les statistiques cumulatives:
   - Si des statistiques existent déjà, la durée est ajoutée au total existant
   - Sinon, de nouvelles statistiques sont créées avec la durée initiale
4. Les durées sont stockées en format `timedelta` de Python, permettant une précision à la microseconde

## Cycle de Vie d'une Détection

Le cycle complet d'une détection comprend plusieurs étapes:

1. **Détection initiale**: La méthode `process_station_data` est appelée avec les données audio d'une station
2. **Identification**: Le système tente d'identifier la piste en utilisant d'abord une correspondance locale, puis AcoustID, puis Audd
3. **Création ou récupération**: La méthode `_get_or_create_track` est appelée pour créer une nouvelle piste ou récupérer une piste existante
4. **Démarrage du suivi**: La méthode `_start_track_detection` est appelée pour commencer à suivre la piste en cours de lecture
5. **Finalisation**: Lorsque la piste n'est plus détectée ou qu'une nouvelle piste est détectée, la méthode `_end_current_track` est appelée
6. **Enregistrement**: La méthode `_record_play_time` est appelée pour enregistrer la détection et mettre à jour les statistiques

## Limitations du Script de Test

Le script de test `test_multiple_stations.py` ne simule pas le cycle complet de détection et d'enregistrement:

1. Il appelle la méthode `process_station_data` qui identifie correctement les pistes et les enregistre dans la base de données
2. Cependant, il ne simule pas la finalisation des détections, c'est-à-dire qu'il n'appelle pas la méthode `_end_current_track`
3. Par conséquent, la méthode `_record_play_time` n'est jamais appelée, et les détections et statistiques ne sont pas enregistrées dans la base de données

Pour tester correctement l'enregistrement des détections et des statistiques, il faudrait:
1. Simuler la détection d'une piste
2. Attendre un certain temps
3. Simuler la fin de la détection (soit en détectant une nouvelle piste, soit en appelant directement `_end_current_track`)

## Résumé

Le système SODAV Monitor enregistre de manière complète et précise:
- Les codes ISRC pour l'identification standard des enregistrements
- Les labels pour le suivi des maisons de disques
- Les empreintes digitales pour l'identification technique des pistes
- Les temps de lecture exacts pour les calculs de redevances et les analyses statistiques

Ces données sont utilisées pour générer des rapports précis et fiables pour la gestion des droits d'auteur et la distribution des redevances. 