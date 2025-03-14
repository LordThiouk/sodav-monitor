# Monitoring avec Prometheus et Grafana

Ce document explique comment utiliser Prometheus et Grafana pour surveiller les performances et l'état du système SODAV Monitor.

## Vue d'ensemble

Le système SODAV Monitor intègre un système de monitoring complet basé sur Prometheus et Grafana :

- **Prometheus** collecte et stocke les métriques du système
- **Grafana** visualise ces métriques dans des tableaux de bord interactifs
- **Node Exporter** fournit des métriques système détaillées (CPU, mémoire, disque, réseau)

Cette architecture permet de surveiller en temps réel les performances du système, d'identifier les goulots d'étranglement et de détecter les problèmes avant qu'ils n'affectent les utilisateurs.

## Métriques collectées

Le système SODAV Monitor expose les métriques suivantes via Prometheus :

### Métriques HTTP

- `sodav_http_requests_total` - Nombre total de requêtes HTTP par méthode, endpoint et code de statut
- `sodav_http_request_duration_seconds` - Latence des requêtes HTTP en secondes

### Métriques de détection

- `sodav_detections_total` - Nombre total de détections musicales par méthode et statut
- `sodav_detection_duration_seconds` - Temps de détection en secondes
- `sodav_detection_confidence` - Niveau de confiance des détections

### Métriques de base de données

- `sodav_db_query_duration_seconds` - Temps d'exécution des requêtes de base de données
- `sodav_track_count` - Nombre total de pistes dans la base de données
- `sodav_artist_count` - Nombre total d'artistes dans la base de données

### Métriques d'API externes

- `sodav_external_api_requests_total` - Nombre total de requêtes aux API externes
- `sodav_external_api_duration_seconds` - Temps de réponse des API externes

### Métriques système

- `sodav_memory_usage_bytes` - Utilisation de la mémoire en octets
- `sodav_cpu_usage_percent` - Utilisation du CPU en pourcentage
- `sodav_active_stations` - Nombre de stations radio actives

## Accès aux interfaces

- **Prometheus** : http://localhost:9090
- **Grafana** : http://localhost:3001 (identifiants par défaut : admin/admin)

## Tableaux de bord Grafana

Le système SODAV Monitor inclut plusieurs tableaux de bord Grafana préconfigurés :

### Tableau de bord "System Overview"

Ce tableau de bord fournit une vue d'ensemble des performances du système :

- Nombre de requêtes HTTP
- Latence des requêtes HTTP
- Utilisation du CPU et de la mémoire
- Nombre de stations actives
- Nombre de pistes et d'artistes dans la base de données

### Tableau de bord "Détection Musicale"

Ce tableau de bord se concentre sur les performances du système de détection musicale :

- Nombre de détections par méthode
- Temps de détection
- Niveau de confiance des détections
- Temps de réponse des API externes
- Nombre de requêtes aux API externes
- Temps d'exécution des requêtes de base de données

## Configuration

### Configuration de Prometheus

La configuration de Prometheus se trouve dans le fichier `docker/prometheus/prometheus.yml`. Vous pouvez modifier ce fichier pour ajuster les intervalles de scraping ou ajouter de nouvelles cibles.

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'sodav-monitor-backend'
    metrics_path: /api/metrics
    static_configs:
      - targets: ['backend:8000']
    scrape_interval: 10s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

### Configuration de Grafana

La configuration de Grafana se trouve dans les dossiers suivants :

- `docker/grafana/provisioning/datasources/` - Configuration des sources de données
- `docker/grafana/provisioning/dashboards/` - Configuration des tableaux de bord

## Ajout de nouvelles métriques

Pour ajouter de nouvelles métriques au système :

1. Définissez les métriques dans le fichier `backend/utils/metrics.py`
2. Utilisez les décorateurs fournis pour instrumenter votre code
3. Assurez-vous que les métriques sont exposées via l'endpoint `/api/metrics`

Exemple d'ajout d'une nouvelle métrique :

```python
from backend.utils.metrics import Counter

# Définir une nouvelle métrique
MY_COUNTER = Counter(
    'sodav_my_counter_total',
    'Description de ma métrique',
    ['label1', 'label2']
)

# Utiliser la métrique
MY_COUNTER.labels(label1='value1', label2='value2').inc()
```

## Alertes

Prometheus peut être configuré pour déclencher des alertes lorsque certaines conditions sont remplies. Pour configurer des alertes :

1. Créez un fichier de règles d'alerte dans le dossier `docker/prometheus/`
2. Référencez ce fichier dans la configuration de Prometheus
3. Configurez un Alertmanager pour gérer les notifications

Exemple de règle d'alerte :

```yaml
groups:
- name: example
  rules:
  - alert: HighRequestLatency
    expr: sodav_http_request_duration_seconds{quantile="0.95"} > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Latence élevée des requêtes HTTP"
      description: "La latence des requêtes HTTP est supérieure à 1 seconde depuis 5 minutes."
```

## Dépannage

### Prometheus ne collecte pas les métriques

1. Vérifiez que l'endpoint `/api/metrics` est accessible
2. Vérifiez la configuration de Prometheus dans `docker/prometheus/prometheus.yml`
3. Vérifiez les logs de Prometheus : `docker logs sodav-prometheus`

### Grafana n'affiche pas les données

1. Vérifiez que la source de données Prometheus est correctement configurée
2. Vérifiez que Prometheus collecte bien les métriques
3. Vérifiez les requêtes PromQL dans les panneaux Grafana

## Ressources

- [Documentation Prometheus](https://prometheus.io/docs/introduction/overview/)
- [Documentation Grafana](https://grafana.com/docs/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [Grafana Dashboard Examples](https://grafana.com/grafana/dashboards/)
