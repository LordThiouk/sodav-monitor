# Monitoring Intégré dans le Frontend

Ce document explique comment utiliser le système de monitoring intégré directement dans le frontend de SODAV Monitor, sans nécessiter l'installation de Prometheus et Grafana via Docker.

## Vue d'ensemble

Le monitoring intégré dans le frontend offre une alternative légère au stack Prometheus/Grafana traditionnel. Il permet de visualiser les métriques importantes du système directement dans l'interface utilisateur de SODAV Monitor, sans nécessiter d'infrastructure supplémentaire.

## Fonctionnalités

Le monitoring intégré offre les fonctionnalités suivantes :

### Métriques Système
- Utilisation CPU
- Utilisation mémoire
- Temps de réponse API
- Statistiques générales du système

### Métriques de Détection
- Nombre de détections
- Scores de confiance
- Détections par méthode (Local, AcoustID, AudD)
- Stations actives

## Accès au Monitoring

Pour accéder au monitoring intégré :

1. Connectez-vous à l'application SODAV Monitor
2. Cliquez sur "Monitoring" dans la barre de navigation
3. La page de monitoring s'affiche avec les différentes métriques

## Utilisation

### Sélection de la Plage de Temps

Vous pouvez sélectionner différentes plages de temps pour afficher les métriques :
- Dernière heure
- 6 heures
- 12 heures
- 24 heures
- 7 jours

### Navigation entre les Onglets

La page de monitoring est organisée en trois onglets :
1. **Vue d'ensemble** : Affiche un résumé des métriques les plus importantes
2. **Système** : Affiche des métriques détaillées sur les performances du système
3. **Détection** : Affiche des métriques détaillées sur le processus de détection musicale

## Implémentation Technique

### Architecture

Le monitoring intégré est implémenté directement dans le frontend React, utilisant :
- React et Chakra UI pour l'interface utilisateur
- Chart.js et react-chartjs-2 pour les graphiques
- Un service de métriques simulées (en attendant l'intégration avec le backend)

### Intégration avec le Backend

Dans la version actuelle, les données sont simulées dans le frontend. Pour une intégration complète avec le backend :

1. Le backend doit exposer des endpoints pour les métriques :
   - `/api/metrics/system?timeRange={timeRange}`
   - `/api/metrics/detection?timeRange={timeRange}`

2. Ces endpoints doivent renvoyer des données au format compatible avec les interfaces définies dans le frontend.

## Différences avec Prometheus/Grafana

| Fonctionnalité | Monitoring Intégré | Prometheus/Grafana |
|----------------|-------------------|-------------------|
| Installation | Aucune installation requise | Nécessite Docker |
| Personnalisation | Limitée | Très flexible |
| Alertes | Non disponible | Disponible |
| Rétention des données | Limitée | Configurable |
| Ressources système | Légères | Plus importantes |
| Intégration | Intégré à l'application | Système séparé |

## Avantages du Monitoring Intégré

- **Simplicité** : Pas besoin d'installer et de configurer Prometheus et Grafana
- **Légèreté** : Consomme moins de ressources système
- **Intégration** : Fait partie de l'interface utilisateur existante
- **Accessibilité** : Disponible pour tous les utilisateurs de l'application

## Limitations

- **Personnalisation limitée** : Moins flexible que Grafana pour la création de tableaux de bord personnalisés
- **Pas d'alertes** : Ne prend pas en charge les alertes automatiques
- **Rétention limitée** : Ne stocke pas les données historiques sur de longues périodes
- **Métriques limitées** : Ensemble fixe de métriques, contrairement à Prometheus qui peut collecter une grande variété de métriques

## Conclusion

Le monitoring intégré dans le frontend offre une solution légère et facile à utiliser pour surveiller les performances de SODAV Monitor, particulièrement adaptée aux environnements où l'installation de Docker n'est pas possible ou souhaitée. Pour des besoins de monitoring plus avancés, l'installation de Prometheus et Grafana reste recommandée lorsque c'est possible. 