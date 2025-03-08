# Test de Détection Musicale avec AcoustID

Ce document explique comment tester la détection musicale avec l'API AcoustID dans le projet SODAV Monitor.

## Prérequis

1. Une clé API AcoustID valide configurée dans le fichier `.env`
2. L'outil `fpcalc` installé (disponible dans `backend/bin/fpcalc`)
3. Un fichier audio de test (disponible dans `backend/tests/data/audio/`)
4. L'environnement Python avec toutes les dépendances installées

## Méthodes de Test

### 1. Test du Format AcoustID

Pour tester la génération d'empreintes et l'envoi à l'API AcoustID :

```bash
python backend/scripts/detection/external_services/test_acoustid_format.py
```

Ce script effectue les opérations suivantes :
- Génère une empreinte digitale à partir d'un fichier audio de test en utilisant `fpcalc`
- Envoie l'empreinte à l'API AcoustID
- Affiche les résultats de la détection

### 2. Test Simple d'AcoustID

Pour un test basique de l'API AcoustID avec une recherche par métadonnées :

```bash
python backend/scripts/detection/external_services/test_acoustid_simple.py
```

Ce script teste l'API AcoustID en recherchant une piste par artiste et titre.

### 3. Test de l'Outil fpcalc

Pour tester spécifiquement l'outil `fpcalc` utilisé pour générer les empreintes :

```bash
python backend/scripts/detection/external_services/test_acoustid_fpcalc.py
```

Ce script vérifie que `fpcalc` est correctement installé et fonctionnel.

## Optimisations Récentes

### Utilisation de POST au lieu de GET

Une optimisation importante a été apportée pour résoudre le problème d'erreur 413 (Request Entity Too Large) :

- La méthode `detect_track` dans `AcoustIDService` a été modifiée pour utiliser la méthode HTTP POST au lieu de GET
- Cette modification permet d'envoyer des empreintes plus longues à l'API AcoustID sans rencontrer de limitations de taille

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

## Interprétation des Résultats

### Résultats Attendus

Un test réussi devrait afficher des informations comme :
- Empreinte générée avec succès
- Durée du fichier audio
- Réponse de l'API avec statut "ok"
- Résultats de détection (si la piste est reconnue)

### Résolution des Problèmes

Si le test échoue, vérifiez les points suivants :

1. **Clé API invalide** : Vérifiez que votre clé API AcoustID est correctement configurée dans le fichier `.env`
2. **fpcalc non trouvé** : Assurez-vous que l'outil `fpcalc` est correctement installé dans `backend/bin/`
3. **Problèmes réseau** : Assurez-vous que vous avez une connexion Internet active
4. **Fichier audio trop court** : AcoustID nécessite des fichiers audio d'une durée suffisante (idéalement > 30 secondes)
5. **Erreur 413** : Si vous rencontrez encore cette erreur, vérifiez que la modification pour utiliser POST est bien appliquée

## Intégration avec le Processus de Détection Hiérarchique

Pour tester l'intégration d'AcoustID dans le processus de détection hiérarchique complet :

```bash
python backend/scripts/detection/test_detection_hierarchy.py
```

Ce script teste l'ensemble du processus de détection, y compris :
1. Détection locale
2. Détection MusicBrainz par métadonnées
3. Détection AcoustID
4. Détection AudD (comme solution de dernier recours)

## Vérification des Données Enregistrées

Après avoir exécuté les tests, vous pouvez vérifier que les données ont été correctement enregistrées dans la base de données :

```bash
python backend/scripts/database/check_detections.py
```

Ce script affiche les détections récentes, y compris celles effectuées via AcoustID, avec leurs métadonnées associées.

## Notes Importantes

- AcoustID est utilisé comme solution secondaire dans le processus de détection hiérarchique, après la détection locale et avant AudD
- Le service AcoustID est gratuit mais a des limitations de taux (3 requêtes par seconde maximum)
- Les résultats dépendent de la qualité de l'empreinte générée et de la présence de la piste dans la base de données AcoustID
- Les fichiers audio courts peuvent ne pas générer d'empreintes suffisamment distinctives pour être reconnus 