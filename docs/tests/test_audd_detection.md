# Test de Détection Musicale avec AudD

Ce document explique comment tester la détection musicale avec l'API AudD dans le projet SODAV Monitor.

## Prérequis

1. Une clé API AudD valide configurée dans le fichier `.env`
2. Un fichier audio de test (disponible dans `backend/tests/data/audio/`)
3. L'environnement Python avec toutes les dépendances installées

## Méthodes de Test

### 1. Test Direct avec le Script Dédié

Le moyen le plus simple de tester la détection AudD est d'utiliser le script dédié :

```bash
python backend/scripts/detection/test_audd_detection.py
```

Ce script effectue les opérations suivantes :
- Charge un fichier audio de test
- Extrait les caractéristiques audio
- Envoie les données à l'API AudD
- Affiche les résultats détaillés de la détection
- Vérifie l'enregistrement des données dans la base de données

### 2. Test via l'API URL d'AudD

Pour tester la détection AudD en utilisant une URL plutôt qu'un fichier audio local :

```bash
python backend/scripts/detection/external_services/test_audd_url.py
```

Ce script teste la capacité du système à détecter de la musique à partir d'une URL de flux audio.

### 3. Test Simple d'AudD

Pour un test basique de la connexion à l'API AudD :

```bash
python backend/scripts/detection/external_services/test_audd_simple.py
```

Ce script vérifie simplement que la clé API est valide et que le service est accessible.

## Interprétation des Résultats

### Résultats Attendus

Un test réussi devrait afficher des informations comme :
- Titre de la piste détectée
- Artiste
- Album
- ISRC (si disponible)
- Label (si disponible)
- Date de sortie (si disponible)
- Score de confiance
- Durée de lecture

### Résolution des Problèmes

Si le test échoue, vérifiez les points suivants :

1. **Clé API invalide** : Vérifiez que votre clé API AudD est correctement configurée dans le fichier `.env`
2. **Problèmes réseau** : Assurez-vous que vous avez une connexion Internet active
3. **Fichier audio non reconnu** : Essayez avec un autre fichier audio plus connu
4. **Quota API dépassé** : Vérifiez si vous avez dépassé votre quota d'utilisation de l'API AudD

## Intégration avec le Processus de Détection Hiérarchique

Pour tester l'intégration d'AudD dans le processus de détection hiérarchique complet :

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

Ce script affiche les détections récentes, y compris celles effectuées via AudD, avec leurs métadonnées associées.

## Notes Importantes

- AudD est utilisé comme solution de dernier recours dans le processus de détection hiérarchique
- Le service AudD est payant, donc les tests consomment des crédits de votre compte
- Les résultats peuvent varier en fonction de la qualité de l'audio et de la popularité de la piste
- La détection AudD est généralement plus précise pour les morceaux populaires et récents
