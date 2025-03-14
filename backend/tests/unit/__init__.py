"""Tests unitaires pour le système SODAV Monitor.

Ce package contient les tests unitaires organisés par module :

- logs/ : Tests pour le système de journalisation
  - test_log_manager.py : Tests pour le gestionnaire de logs

- utils/ : Tests pour les utilitaires
  - test_auth.py : Tests pour l'authentification
  - test_redis_config.py : Tests pour la configuration Redis
  - test_validators.py : Tests pour les validateurs de données
  - test_stream_checker.py : Tests pour la vérification des flux

- models/ : Tests pour les modèles de données
  - test_isrc_uniqueness.py : Tests pour l'unicité des codes ISRC

- detection/ : Tests pour la détection musicale
  - test_station_detection.py : Tests pour la détection sur les stations

- analytics/ : Tests pour les analyses et statistiques
  - test_stats_updater.py : Tests pour la mise à jour des statistiques

- core/ : Tests pour les fonctionnalités de base
  - test_error_recovery.py : Tests pour la récupération d'erreurs

- api/ : Tests pour les endpoints API

Ces tests vérifient que chaque composant fonctionne correctement de manière isolée.
"""
