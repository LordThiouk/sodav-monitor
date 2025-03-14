# Scripts de Test des Services Externes de Détection Musicale

Ce dossier contient des scripts pour tester les services externes de détection musicale utilisés dans le projet SODAV Monitor.

## Organisation des scripts

### Tests MusicBrainz

- `test_musicbrainz_simple.py` - Test simple de l'API MusicBrainz
- `test_musicbrainz_metadata.py` - Test de la recherche par métadonnées avec MusicBrainz

### Tests AcoustID

- `test_acoustid_simple.py` - Test simple de l'API AcoustID
- `test_acoustid_format.py` - Test des formats audio avec AcoustID
- `test_acoustid_fpcalc.py` - Test de l'outil fpcalc pour AcoustID

### Tests AudD

- `test_audd_simple.py` - Test simple de l'API AudD
- `test_audd_url.py` - Test de l'API AudD avec des URLs
- `test_audd_url_simple.py` - Test simple de l'API AudD avec des URLs

### Tests combinés

- `test_api_keys.py` - Test des clés API pour tous les services externes
- `test_external_services.py` - Test de tous les services externes

## Comment exécuter les scripts

Pour exécuter un script, utilisez la commande suivante depuis la racine du projet :

```bash
python backend/scripts/detection/external_services/nom_du_script.py
```

Par exemple, pour tester l'API MusicBrainz :

```bash
python backend/scripts/detection/external_services/test_musicbrainz_simple.py
```

## Résultats des tests

Les résultats des tests sont affichés dans la console et également enregistrés dans les logs de l'application. Vous pouvez consulter les logs spécifiques aux services externes dans les fichiers suivants :

- `backend/logs/categories/musicbrainz.log` - Logs spécifiques à MusicBrainz
- `backend/logs/categories/audd.log` - Logs spécifiques à AudD

## Dépannage

Si vous rencontrez des problèmes lors de l'exécution des scripts, vérifiez les points suivants :

1. Assurez-vous que les clés API sont correctement configurées dans le fichier `.env`
2. Vérifiez que vous avez une connexion Internet active
3. Consultez les logs pour plus de détails sur les erreurs rencontrées

Pour plus d'informations sur les services externes, consultez la documentation complète dans le fichier `docs/external_services.md` à la racine du projet.
