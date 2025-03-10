# Architecture du Système

Ce dossier contient la documentation relative à l'architecture globale du système SODAV Monitor.

## Contenu

- **system_architecture.md** : Vue d'ensemble de l'architecture du système
- **component_diagram.md** : Diagramme des composants et leurs interactions
- **data_flow.md** : Flux de données dans le système
- **design_decisions.md** : Décisions de conception importantes et leur justification
- **[c4_model/](c4_model/)** : Documentation de l'architecture selon le modèle C4

## Organisation du Projet

Pour une vue d'ensemble de l'organisation du projet et des changements structurels récents, consultez [reorganisation.md](reorganisation.md).

## C4 Model

Le [C4 Model](c4_model/) est une approche de documentation architecturale qui utilise quatre niveaux de diagrammes pour visualiser l'architecture logicielle à différents niveaux d'abstraction:

1. **[Contexte](c4_model/1_context.md)** - Vue d'ensemble du système et de son environnement
2. **[Conteneurs](c4_model/2_containers.md)** - Décomposition du système en conteneurs de haut niveau
3. **[Composants](c4_model/3_components/)** - Décomposition de chaque conteneur en composants
4. **[Code](c4_model/4_code/)** - Implémentation détaillée des composants clés

Cette approche facilite la communication entre les parties prenantes techniques et non techniques en fournissant une vue progressive de l'architecture, du plus général au plus détaillé. 