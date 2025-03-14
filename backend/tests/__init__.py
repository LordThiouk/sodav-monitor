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
  - test_end_to_end.py: Tests de bout en bout (E2E)
  - README_E2E_TESTS.md: Documentation des tests E2E
  - E2E_COMPLIANCE.md: Conformité des tests E2E avec les règles établies

Les tests E2E suivent des règles strictes pour garantir une couverture complète:
1. Principes généraux: Tester le système entier, utiliser des scénarios réels
2. Workflow de détection: Vérifier le type d'audio, suivre la hiérarchie de détection
3. Précision de la durée de lecture: Enregistrer les horodatages, calculer la durée exacte
4. Validation des stations: Tester les flux en direct, vérifier les métadonnées
5. Génération de rapports: Vérifier le contenu et la précision des rapports
6. Performance: Tester la charge du système et le traitement de données
7. Cohérence de la base de données: Éviter les doublons, assurer l'intégrité

Pour plus de détails, voir integration/E2E_COMPLIANCE.md et integration/README_E2E_TESTS.md
"""

# Import only what's needed for basic test setup
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
