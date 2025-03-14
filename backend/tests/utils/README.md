# Simulateur de Radio Amélioré pour SODAV Monitor

Ce répertoire contient des outils pour simuler des stations de radio et tester la détection musicale dans le cadre du projet SODAV Monitor.

## Composants Principaux

### 1. Simulateur de Radio Amélioré (`enhanced_radio_simulator.py`)

Version améliorée du simulateur de radio avec des fonctionnalités supplémentaires pour les tests de détection musicale :

- Diffusion de flux audio en continu
- Simulation réaliste de stations de radio
- Enregistrement précis de la durée de lecture
- Logs détaillés pour analyse
- Simulation d'interruptions et de conditions réelles
- Monitoring en temps réel
- Export des logs en CSV ou JSON

### 2. Script d'Exécution (`run_senegal_radio_enhanced.py`)

Script pour exécuter facilement le simulateur de radio amélioré avec les fichiers audio sénégalais. Fonctionnalités :

- Interface utilisateur en ligne de commande
- Commandes pour simuler des interruptions
- Sélection manuelle de morceaux
- Export des logs

### 3. Script de Test de Détection (`test_detection_with_enhanced_simulator.py`)

Script pour tester la détection musicale avec le simulateur de radio amélioré :

- Capture du flux audio d'une station simulée
- Détection musicale
- Comparaison des résultats de détection avec les logs de diffusion
- Évaluation de la précision

## Prérequis

- Python 3.8+
- Fichiers audio MP3 dans le répertoire `tests/data/audio/senegal`
- `fpcalc.exe` dans le répertoire `bin/` (pour la génération d'empreintes acoustiques)

## Utilisation

### Exécuter le Simulateur de Radio

```bash
python -m tests.utils.run_senegal_radio_enhanced
```

Commandes disponibles :
- `i` - Simuler une interruption
- `s <index>` - Sélectionner un morceau (ex: `s 1`)
- `e` - Exporter les logs
- `q` - Quitter

### Tester la Détection Musicale

```bash
python -m tests.utils.test_detection_with_enhanced_simulator
```

Ce script effectue automatiquement :
1. Configuration de la base de données en mémoire
2. Création des données de test (artiste, pistes)
3. Génération des empreintes acoustiques
4. Création d'une station de radio simulée
5. Capture audio et détection musicale
6. Analyse des résultats et export des logs

## Structure des Logs

Les logs générés contiennent des informations détaillées sur :

- Les événements de lecture (début/fin de morceau)
- Les interruptions simulées
- Les détections musicales
- Les correspondances trouvées

Format des logs :
```json
{
  "play_logs": [
    {
      "timestamp": "2023-03-14T12:30:45",
      "station_name": "Radio Sénégal",
      "event_type": "track_start",
      "track_name": "DIP DOUNDOU GUISS - CALIFAT",
      "duration": 0,
      "details": {}
    },
    ...
  ],
  "detection_logs": [
    {
      "timestamp": "2023-03-14T12:31:15",
      "station_name": "Radio Sénégal Test",
      "track_name": "DIP DOUNDOU GUISS - CALIFAT",
      "detection_method": "fingerprint",
      "confidence": 0.95,
      "play_duration": 30.5,
      "fingerprint": "...",
      "metadata": {"detection_index": 1}
    },
    ...
  ]
}
```

## Mesure de la Précision

Le simulateur permet de mesurer la précision de la détection en comparant :

- Les morceaux réellement diffusés (logs de lecture)
- Les morceaux détectés (logs de détection)
- Les durées de lecture réelles vs. détectées

Métriques calculées :
- Taux de détection correct
- Précision des durées de lecture
- Temps de réponse de la détection

## Extension

Pour ajouter de nouveaux fichiers audio :
1. Placez les fichiers MP3 dans `tests/data/audio/senegal`
2. Exécutez le script `copy_downloaded_audio.py` si les fichiers sont dans le dossier Téléchargements

Pour créer de nouvelles stations :
```python
simulator = EnhancedRadioSimulator()
station = simulator.create_station(
    name="Nouvelle Station",
    audio_dir=AUDIO_DIR,
    genre="Genre",
    country="Pays",
    language="Langue"
)
``` 