# Index de la Documentation SODAV Monitor

## Architecture
- [Architecture du Système](architecture/README.md)
- [Réorganisation du Projet](architecture/reorganisation.md)
- [C4 Model](architecture/c4_model/README.md)
  - [Diagramme de Contexte](architecture/c4_model/1_context.md)
  - [Diagramme de Conteneurs](architecture/c4_model/2_containers.md)
  - [Diagrammes de Composants](architecture/c4_model/3_components/)
    - [Composants du Backend](architecture/c4_model/3_components/backend_components.md)
    - [Composants du Frontend](architecture/c4_model/3_components/frontend_components.md)
    - [Composants de Détection](architecture/c4_model/3_components/detection_components.md)
  - [Diagrammes de Code](architecture/c4_model/4_code/)
    - [Validateur ISRC](architecture/c4_model/4_code/isrc_validator.md)

## API
- [Documentation de l'API](api/README.md)
- [Vue d'ensemble de l'API](api/api_overview.md)
- [Services Externes](api/external_services.md)
- [Intégration AcoustID](api/integration/acoustid_usage.md)
- [Détection par Station](api/integration/station_detection.md)

## Base de Données
- [Documentation de la Base de Données](database/README.md)
- [Stockage des Données](database/data_storage.md)
- [Contrainte d'Unicité ISRC](database/migrations/isrc_unique_constraint.md)
- [Améliorations des Détections de Pistes](database/migrations/track_detection_enhancements.md)

## Détection
- [Documentation du Système de Détection](detection/README.md)
- [Cycle de Vie d'une Détection](detection/detection_lifecycle.md)
- [Recommandations pour la Détection](detection/detection_recommendations.md)
- [Structure des Empreintes Digitales](detection/fingerprint_structure.md)
- [Détection Locale](detection/local_detection.md)
- [Détection de Musique Africaine](detection/african_music_detection.md)
- [Améliorations de la Détection](detection/detection_improvements.md)
- [Réutilisation des Empreintes](detection/fingerprint_reuse.md)
- [Bonnes Pratiques ISRC](detection/isrc_best_practices.md)

## Développement
- [Guide de Développement](development/README.md)
- [Standards de Documentation](development/documentation_standards.md)
- [Configuration de Sphinx](development/sphinx_setup.md)
- [Modernisation](development/modernization.md)

## Sécurité
- [Sécurité](security/README.md)
- [Directives de Sécurité](security/security_guidelines.md)

## Performance
- [Performance](performance/README.md)
- [Tests de Performance](performance/performance_testing.md)
- [Suivi de la Durée de Lecture](performance/play_duration_tracking.md)
- [Monitoring avec Prometheus et Grafana](performance/monitoring.md)
- [Monitoring Intégré dans le Frontend](performance/frontend_monitoring.md)

## Tests
- [Tests](tests/README.md)
- [Stratégie de Test](tests/testing_strategy.md)
- [Tests d'Intégration](tests/integration_testing.md)
- [Guide des Tests Unitaires](tests/unit_testing_guide.md)
- [Test de la Contrainte d'Unicité ISRC](tests/isrc_uniqueness_test.md)
- [Test de Détection AcoustID](tests/test_acoustid_detection.md)
- [Test de Détection AudD](tests/test_audd_detection.md)
- [Guide de Test de Détection](tests/detection_testing_guide.md)

## Résolution des Problèmes
- [Résolution des Problèmes](troubleshooting/README.md)
- [Problèmes d'Intégration AcoustID](troubleshooting/acoustid_integration.md)
- [Problèmes de Mise à Jour des Statistiques](troubleshooting/stats_update_issues.md)

## Documentation Générée
- [Documentation Sphinx](sphinx/build/html/index.html)

## Mises à Jour Récentes

### Mars 2025

- ✅ **Amélioration majeure du suivi du temps de diffusion** : Le système a été amélioré pour distinguer clairement entre la durée d'échantillon audio et la durée réelle de diffusion. Cette distinction est primordiale pour le calcul précis des redevances. Voir [Suivi de la Durée de Lecture](performance/play_duration_tracking.md) et [Problèmes de Mise à Jour des Statistiques](troubleshooting/stats_update_issues.md) pour plus de détails.

- ✅ **Résolution du problème du temps de jeu** : Le système de suivi du temps de jeu a été corrigé et validé par des tests d'intégration. Les durées de lecture sont maintenant correctement calculées, transmises et accumulées dans les statistiques.

- ✅ **Amélioration des tests d'intégration** : Les tests d'intégration ont été améliorés pour vérifier l'accumulation correcte des statistiques, notamment pour les durées de lecture. Voir [Tests d'Intégration](tests/integration_testing.md) pour plus de détails.

- ✅ **Documentation mise à jour** : La documentation a été mise à jour pour refléter les changements récents et fournir des informations plus détaillées sur le système de suivi du temps de jeu. 