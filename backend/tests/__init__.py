"""Test suite for the SODAV Monitor backend.

Structure:
- unit/: Tests unitaires
  - analytics/: Tests des fonctionnalités d'analyse
  - api/: Tests des endpoints API
  - auth/: Tests d'authentification
  - core/: Tests des fonctionnalités de base
  - detection/: Tests de détection musicale
  - logs/: Tests du système de journalisation
  - models/: Tests des modèles de données
  - performance/: Tests de performance
  - reports/: Tests de génération de rapports
  - stream_handler/: Tests de gestion des flux
  - utils/: Tests des utilitaires

- integration/: Tests d'intégration
  - analytics/: Tests d'intégration des analyses
  - api/: Tests d'intégration des API
  - detection/: Tests d'intégration de détection
  - test_end_to_end.py: Tests de bout en bout
"""

# Import only what's needed for basic test setup
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
