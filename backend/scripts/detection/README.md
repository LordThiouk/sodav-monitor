# Scripts de Détection Musicale

Ce dossier contient des scripts pour tester et gérer la détection musicale dans le projet SODAV Monitor.

## Organisation des scripts

- `test_detection_hierarchy.py` - Test du processus de détection hiérarchique complet
- `test_fingerprint_reuse.py` - Test de la réutilisation des empreintes digitales
- `test_local_detection.py` - Test de la détection locale avec les empreintes stockées
- `test_audd_detection.py` - Test de la détection AudD
- `external_services/` - Scripts pour tester les services externes de détection musicale

## Test du processus de détection hiérarchique

Le script `test_detection_hierarchy.py` teste l'ensemble du processus de détection hiérarchique, qui comprend :

1. Détection locale
2. Détection MusicBrainz par métadonnées
3. Détection AcoustID
4. Détection AudD

Ce script utilise un fichier audio de test pour simuler le processus de détection et affiche les résultats de chaque étape.

## Test de réutilisation des empreintes digitales

Le script `test_fingerprint_reuse.py` teste spécifiquement la fonctionnalité de réutilisation des empreintes digitales :

1. Création d'une piste de test avec une empreinte digitale unique
2. Simulation d'une détection avec la même empreinte digitale
3. Vérification que la piste est correctement identifiée via la détection locale

Cette fonctionnalité est essentielle pour réduire la dépendance aux API externes et améliorer les performances de détection.

## Test de détection locale

Le script `test_local_detection.py` teste la détection locale avec les empreintes stockées :

1. Création de plusieurs pistes de test avec des empreintes digitales uniques
2. Simulation de détections avec différentes empreintes
3. Vérification que les pistes sont correctement identifiées via la détection locale
4. Test des cas limites (empreintes similaires, empreintes inexistantes)

## Test de détection AudD

Le script `test_audd_detection.py` teste spécifiquement la détection via l'API AudD :

1. Chargement d'un fichier audio de test
2. Envoi du fichier à l'API AudD
3. Traitement et affichage des résultats de la détection

## Comment exécuter les scripts

Pour exécuter un script de test, utilisez la commande suivante depuis la racine du projet :

```bash
python backend/scripts/detection/nom_du_script.py
```

Par exemple, pour tester la réutilisation des empreintes digitales :

```bash
python backend/scripts/detection/test_fingerprint_reuse.py
```

## Résultats des tests

Les résultats des tests sont affichés dans la console et également enregistrés dans les logs de l'application. Vous pouvez consulter les logs spécifiques à la détection dans le fichier `backend/logs/categories/detection.log`.

## Dépannage

Si vous rencontrez des problèmes lors de l'exécution des scripts, vérifiez les points suivants :

1. Assurez-vous que le fichier audio de test existe dans le chemin spécifié
2. Vérifiez que les clés API pour les services externes sont correctement configurées dans le fichier `.env`
3. Consultez les logs pour plus de détails sur les erreurs rencontrées
4. Assurez-vous que la base de données est accessible et correctement configurée

Pour plus d'informations sur le processus de détection hiérarchique et la réutilisation des empreintes digitales, consultez la documentation complète dans les fichiers suivants :
- `docs/external_services.md` : Documentation sur les services externes de détection musicale
- `docs/fingerprint_reuse.md` : Documentation détaillée sur la réutilisation des empreintes digitales
