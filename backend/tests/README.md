# Tests pour SODAV Monitor

Ce répertoire contient tous les tests pour le backend du projet SODAV Monitor.

## Nouvelle Organisation des Tests

Les tests sont maintenant organisés en deux catégories principales :

### 1. Tests Unitaires (`unit/`)

Les tests unitaires sont organisés par module et testent des composants individuels de manière isolée :

- `logs/` : Tests pour le système de journalisation
- `utils/` : Tests pour les utilitaires
- `models/` : Tests pour les modèles de données
- `detection/` : Tests pour la détection musicale
- `analytics/` : Tests pour les analyses et statistiques
- `core/` : Tests pour les fonctionnalités de base
- `api/` : Tests pour les endpoints API

### 2. Tests d'Intégration (`integration/`)

Les tests d'intégration vérifient l'interaction entre plusieurs composants :

- `analytics/` : Tests d'intégration pour les analyses
- `detection/` : Tests d'intégration pour la détection
- `api/` : Tests d'intégration pour les API
- `test_end_to_end.py` : Tests de bout en bout du système complet

## Exécution des Tests

### Exécuter tous les tests
```bash
python -m pytest
```

### Exécuter uniquement les tests unitaires
```bash
python -m pytest tests/unit/
```

### Exécuter uniquement les tests d'intégration
```bash
python -m pytest tests/integration/
```

### Exécuter les tests d'un module spécifique
```bash
python -m pytest tests/unit/logs/
```

## Couverture des Tests

Pour générer un rapport de couverture des tests :

```bash
# Générer un rapport de couverture
python -m pytest --cov=backend backend/tests/

# Générer un rapport HTML détaillé
python -m pytest --cov=backend --cov-report=html backend/tests/
```

Le rapport HTML sera disponible dans le répertoire `htmlcov/`.

## Bonnes Pratiques

1. **Isolation** : Chaque test doit être indépendant des autres
2. **Mocks** : Utiliser des mocks pour les dépendances externes
3. **Fixtures** : Utiliser des fixtures pour partager la configuration
4. **Nommage** : Suivre la convention de nommage `test_<fonction_testée>.py`
5. **Documentation** : Documenter les tests complexes
6. **Couverture** : Viser une couverture de code d'au moins 90%
7. **Données de Test** : Utiliser des données de test réalistes
8. **Performance** : Optimiser les tests pour qu'ils s'exécutent rapidement

## Tests avec Données Réelles

Pour les tests nécessitant des données réelles (comme les tests de détection musicale), nous utilisons :

1. **Fichiers Audio de Test** : Stockés dans `backend/tests/data/audio/`
2. **Flux Radio Réels** : Stations de radio sénégalaises accessibles via Internet
3. **Empreintes Digitales** : Empreintes digitales pré-calculées pour les tests

Pour les tests end-to-end, nous utilisons des stations de radio sénégalaises réelles pour garantir des conditions de test authentiques.
