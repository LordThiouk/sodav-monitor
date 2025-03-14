# Guide de Test du Système de Détection Musicale

Ce document sert de guide principal pour tester le système de détection musicale du projet SODAV Monitor. Il référence les différents tests disponibles et explique comment les utiliser.

## Vue d'ensemble du Système de Détection

Le système de détection musicale de SODAV Monitor utilise une approche hiérarchique pour identifier les pistes musicales :

1. **Détection Locale** : Recherche dans la base de données locale à l'aide des empreintes digitales stockées
2. **Détection MusicBrainz** : Utilise les métadonnées pour rechercher dans MusicBrainz
3. **Détection AcoustID** : Génère une empreinte digitale et la compare avec la base de données AcoustID
4. **Détection AudD** : Solution de dernier recours, utilise le service payant AudD

## Tests Disponibles

### Tests du Processus Complet

- **Test de la Hiérarchie de Détection** : Teste l'ensemble du processus de détection hiérarchique
  ```bash
  python backend/scripts/detection/test_detection_hierarchy.py
  ```

- **Test avec Fichier Connu** : Teste la détection avec un fichier audio connu
  ```bash
  python backend/scripts/detection/test_detection_with_known_file.py
  ```

### Tests des Services Individuels

- **Test de Détection Locale** : Teste la détection locale avec les empreintes stockées
  ```bash
  python backend/scripts/detection/test_local_detection.py
  ```

- **Test de Détection AcoustID** : Guide pour tester la détection avec AcoustID
  Voir le document détaillé : [Test de Détection AcoustID](test_acoustid_detection.md)

- **Test de Détection AudD** : Guide pour tester la détection avec AudD
  Voir le document détaillé : [Test de Détection AudD](test_audd_detection.md)

### Tests des Services Externes

#### AcoustID
- **Test du Format AcoustID** : Teste la génération d'empreintes et l'envoi à l'API
  ```bash
  python backend/scripts/detection/external_services/test_acoustid_format.py
  ```

- **Test Simple d'AcoustID** : Teste l'API avec une recherche par métadonnées
  ```bash
  python backend/scripts/detection/external_services/test_acoustid_simple.py
  ```

- **Test de l'Outil fpcalc** : Teste l'outil de génération d'empreintes
  ```bash
  python backend/scripts/detection/external_services/test_acoustid_fpcalc.py
  ```

#### AudD
- **Test de Détection AudD** : Teste la détection avec l'API AudD
  ```bash
  python backend/scripts/detection/test_audd_detection.py
  ```

- **Test d'AudD avec URL** : Teste la détection à partir d'une URL
  ```bash
  python backend/scripts/detection/external_services/test_audd_url.py
  ```

- **Test Simple d'AudD** : Teste la connexion à l'API AudD
  ```bash
  python backend/scripts/detection/external_services/test_audd_simple.py
  ```

#### MusicBrainz
- **Test Simple de MusicBrainz** : Teste l'API MusicBrainz
  ```bash
  python backend/scripts/detection/external_services/test_musicbrainz_simple.py
  ```

- **Test de MusicBrainz avec Métadonnées** : Teste la recherche par métadonnées
  ```bash
  python backend/scripts/detection/external_services/test_musicbrainz_metadata.py
  ```

### Tests des Clés API

- **Test des Clés API** : Vérifie que toutes les clés API sont valides
  ```bash
  python backend/scripts/detection/external_services/test_api_keys.py
  ```

## Comment Exécuter les Tests

### Prérequis

1. Assurez-vous que toutes les clés API nécessaires sont configurées dans le fichier `.env` :
   - `ACOUSTID_API_KEY` pour AcoustID
   - `AUDD_API_KEY` pour AudD

2. Vérifiez que l'outil `fpcalc` est correctement installé dans `backend/bin/`

3. Assurez-vous que les fichiers audio de test sont disponibles dans `backend/tests/data/audio/`

### Exécution des Tests

Pour exécuter un test, utilisez la commande suivante depuis la racine du projet :

```bash
python <chemin_vers_le_script_de_test>
```

Par exemple, pour tester la hiérarchie de détection complète :

```bash
python backend/scripts/detection/test_detection_hierarchy.py
```

## Résolution des Problèmes Courants

### Problèmes avec AcoustID

Si vous rencontrez des erreurs avec AcoustID, consultez le [guide de test AcoustID](test_acoustid_detection.md) pour des solutions spécifiques, notamment :
- Erreur 413 (Request Entity Too Large)
- Problèmes avec l'outil fpcalc
- Absence de résultats pour des fichiers courts

### Problèmes avec AudD

Si vous rencontrez des erreurs avec AudD, consultez le [guide de test AudD](test_audd_detection.md) pour des solutions spécifiques, notamment :
- Problèmes de clé API
- Quotas dépassés
- Fichiers non reconnus

## Optimisations Récentes

### Utilisation de POST pour AcoustID

Une optimisation importante a été apportée pour résoudre le problème d'erreur 413 avec AcoustID :
- La méthode HTTP POST est maintenant utilisée au lieu de GET
- Cette modification permet d'envoyer des empreintes plus longues sans limitations de taille

Avant la modification :
```python
async with session.get(url, params=params, timeout=30) as response:
    # Traitement de la réponse
```

Après la modification :
```python
async with session.post(url, data=params, timeout=30) as response:
    # Traitement de la réponse
```

### Réutilisation des Empreintes

Le système a été amélioré pour réutiliser les empreintes digitales stockées :
- Les empreintes sont stockées lors de la première détection
- Les détections suivantes utilisent d'abord la base de données locale
- Cette optimisation réduit la dépendance aux API externes

## Vérification des Résultats

Après avoir exécuté les tests, vous pouvez vérifier les résultats dans les logs et la base de données :

```bash
# Vérifier les logs de détection
tail -f backend/logs/categories/detection.log

# Vérifier les détections récentes dans la base de données
python backend/scripts/database/check_detections.py
```
