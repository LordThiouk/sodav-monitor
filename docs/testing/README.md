# Outils de Test pour SODAV Monitor

Ce dossier contient la documentation des différents outils de test disponibles pour le projet SODAV Monitor.

## Guides Disponibles

- [Guide d'Utilisation du Simulateur de Radio](radio_simulator_guide.md) - Guide complet pour utiliser le simulateur de radio amélioré pour tester la détection musicale.
- [Guide d'Exécution des Tests](running_tests.md) - Instructions pour exécuter les différents types de tests du projet.

## Outils de Test

### Simulateur de Radio

Le simulateur de radio est un outil essentiel pour tester le système de détection musicale en conditions réelles. Il permet de :

- Diffuser des flux audio en continu via HTTP
- Simuler plusieurs stations de radio avec des playlists personnalisées
- Enregistrer avec précision les durées de lecture
- Simuler des interruptions de flux
- Tester la détection musicale avec de vrais appels API

Pour plus d'informations, consultez le [Guide d'Utilisation du Simulateur de Radio](radio_simulator_guide.md).

### Tests de Détection Musicale

Plusieurs scripts sont disponibles pour tester la détection musicale :

1. **Test Simple** (`simple_detection_test.py`) - Test basique de détection musicale avec simulation.
2. **Test avec API Réelles** (`real_api_detection_test.py`) - Test utilisant de vrais appels API (locale, MusicBrainz, Audd.io).
3. **Test Multi-Stations** (`multi_station_test.py`) - Test avec plusieurs stations simultanées.

### Visualisation des Résultats

L'outil de visualisation des résultats (`visualize_detection_results.py`) permet de générer des graphiques et des rapports à partir des logs de détection. Il offre :

- Des graphiques de chronologie des détections
- Des statistiques sur les méthodes de détection utilisées
- Des graphiques de répartition par station
- Des histogrammes de niveaux de confiance
- Des rapports détaillés au format texte et HTML

Pour exécuter la visualisation :
```bash
python -m backend.tests.utils.run_visualize_detection_results --log-file <fichier_logs.json>
```

## Exécution des Tests

### Test Simple
```bash
python -m backend.tests.utils.simple_detection_test
```

### Test avec API Réelles
```bash
python -m backend.tests.utils.run_real_api_detection
```

### Test Multi-Stations
```bash
python -m backend.tests.utils.run_multi_station_test
```

Options disponibles pour le test multi-stations :
- `--acoustid-key` : Clé API AcoustID
- `--audd-key` : Clé API Audd.io
- `--stations` : Nombre de stations à simuler (défaut: 3)
- `--detections` : Nombre de détections par station (défaut: 2)
- `--duration` : Durée de chaque détection en secondes (défaut: 15)

### Visualisation des Résultats
```bash
python -m backend.tests.utils.run_visualize_detection_results
```

Options disponibles pour la visualisation :
- `--log-file` : Fichier de logs JSON à analyser
- `--output-dir` : Répertoire de sortie pour les rapports
- `--format` : Format du rapport (text, html, both)
- `--show-plots` : Afficher les graphiques à l'écran

## Préparation des Fichiers Audio

Pour préparer les fichiers audio nécessaires aux tests :

1. **Copier des fichiers depuis le dossier Téléchargements** :
   ```bash
   python -m backend.tests.utils.copy_downloaded_audio
   ```

2. **Télécharger des fichiers audio de test** :
   ```bash
   python -m backend.tests.utils.download_test_audio_direct
   ```

## Intégration avec le Système de Détection

Les tests s'intègrent parfaitement avec le système de détection musicale existant, utilisant la hiérarchie de détection suivante :

1. Détection locale (empreintes acoustiques)
2. MusicBrainz API
3. Audd.io API

Chaque détection est enregistrée avec des métadonnées détaillées, incluant la méthode utilisée, le niveau de confiance, et la durée de lecture. 