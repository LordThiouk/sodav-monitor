# Détection de la Musique Africaine dans SODAV Monitor

Ce document détaille les défis spécifiques, les résultats de tests et les recommandations pour améliorer la détection de la musique africaine, en particulier sénégalaise, dans le système SODAV Monitor.

## 1. Défis Spécifiques

La détection de la musique africaine présente plusieurs défis particuliers :

1. **Sous-représentation dans les bases de données internationales** :
   - Les services comme AcoustID et MusicBrainz contiennent moins d'entrées pour la musique africaine
   - Les empreintes digitales de morceaux africains sont moins nombreuses dans ces bases de données

2. **Particularités acoustiques** :
   - Instruments traditionnels africains avec des signatures acoustiques uniques
   - Rythmes et structures musicales différents des standards occidentaux
   - Variations vocales et techniques de chant spécifiques

3. **Métadonnées incomplètes ou inconsistantes** :
   - Orthographes variables des noms d'artistes et titres
   - Translittérations différentes selon les sources
   - Informations de label et ISRC parfois manquantes

4. **Caractères spéciaux et langues locales** :
   - Utilisation de caractères spéciaux (comme dans "Dëgg La")
   - Titres en langues locales pouvant causer des problèmes d'encodage

## 2. Résultats des Tests

Des tests ont été réalisés avec plusieurs échantillons de musique sénégalaise, dont "Dëgg La" par Pape Diouf. Voici les principaux résultats :

### 2.1 Performance des Services de Détection

| Service | Taux de Réussite | Qualité des Métadonnées | Observations |
|---------|-----------------|------------------------|--------------|
| AcoustID | Faible (< 10%) | Limitée | Échec systématique pour la musique africaine |
| AudD | Élevé (> 80%) | Excellente | Fournit ISRC, label, date de sortie |
| Détection locale | Moyenne (50%) | Bonne | Dépend de l'enrichissement préalable de la base |

### 2.2 Problèmes Identifiés

1. **Problème de mise à jour des métadonnées** :
   ```
   [AUDD] AudD found track: Dëgg La by Pape Diouf
   [AUDD] ISRC found in Apple Music data: FR10S1455141
   [AUDD] AudD detection result: Dëgg La by Pape Diouf
   ```
   Malgré cette détection réussie, la piste a été enregistrée comme "Unknown Track" par "Unknown Artist".

2. **Incohérences dans les données sauvegardées** :
   - L'ISRC détecté n'est pas toujours sauvegardé dans la base de données
   - Le label "Prince Arts" n'a pas été enregistré malgré sa présence dans les données AudD
   - L'album "Ràkkaaju" n'a pas été correctement enregistré

3. **Problèmes avec les caractères spéciaux** :
   - Les caractères comme "ë" dans "Dëgg" peuvent causer des problèmes d'encodage
   - Certains noms d'artistes ou titres peuvent être mal interprétés

## 3. Recommandations

### 3.1 Améliorations Techniques

1. **Modification de la hiérarchie de détection pour la musique africaine** :
   ```python
   # Configuration par station
   station_config = {
       "dakar_musique": {
           "detection_priority": ["audd", "local", "acoustid"]
       },
       "default": {
           "detection_priority": ["local", "acoustid", "audd"]
       }
   }
   ```

2. **Correction de la méthode `find_audd_match`** :
   - Ajouter des vérifications pour s'assurer que les métadonnées sont correctement extraites
   - Implémenter un système de validation des métadonnées avant sauvegarde
   - Ajouter des logs détaillés pour suivre le processus de mise à jour

3. **Gestion améliorée des caractères spéciaux** :
   - Normaliser les chaînes de caractères avant comparaison
   - Utiliser des techniques de correspondance floue pour les titres et noms d'artistes

### 3.2 Enrichissement de la Base de Données

1. **Création d'une base de données spécialisée** :
   - Collecter et indexer des empreintes digitales de musique africaine
   - Organiser des sessions d'enregistrement pour les artistes locaux

2. **Partenariats avec des labels africains** :
   - Établir des partenariats avec des labels comme Prince Arts
   - Obtenir des catalogues complets avec métadonnées

3. **Intégration avec des sources locales** :
   - Se connecter à des bases de données musicales spécifiques à l'Afrique
   - Développer des API d'intégration avec des services locaux

### 3.3 Améliorations du Processus de Test

1. **Création d'un jeu de test spécifique** :
   - Constituer une bibliothèque de test de musique africaine
   - Documenter les métadonnées attendues pour chaque morceau

2. **Métriques de performance dédiées** :
   - Mesurer séparément les performances sur la musique africaine
   - Établir des objectifs spécifiques d'amélioration

## 4. Plan d'Implémentation

| Priorité | Action | Complexité | Impact |
|----------|--------|------------|--------|
| 1 | Corriger la méthode `find_audd_match` | Moyenne | Élevé |
| 2 | Implémenter la configuration par station | Faible | Élevé |
| 3 | Améliorer la gestion des caractères spéciaux | Moyenne | Moyen |
| 4 | Créer un jeu de test spécifique | Faible | Moyen |
| 5 | Établir des partenariats avec des labels | Élevée | Élevé |

## 5. Conclusion

L'amélioration de la détection de la musique africaine est essentielle pour le succès du projet SODAV Monitor au Sénégal. Les tests ont montré que le service AudD offre les meilleures performances pour ce type de contenu, mais des problèmes subsistent dans le traitement et l'enregistrement des métadonnées.

En mettant en œuvre les recommandations de ce document, le système pourra atteindre un taux de détection beaucoup plus élevé pour la musique africaine, contribuant ainsi à une meilleure gestion des droits d'auteur pour les artistes locaux. 