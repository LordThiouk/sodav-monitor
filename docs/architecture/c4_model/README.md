# C4 Model pour SODAV Monitor

Ce dossier contient la documentation architecturale du projet SODAV Monitor selon le modèle C4, développé par Simon Brown. Le C4 Model permet de visualiser l'architecture logicielle à différents niveaux d'abstraction, facilitant ainsi la communication entre les parties prenantes techniques et non techniques.

## Qu'est-ce que le C4 Model?

Le C4 Model est une approche de documentation architecturale qui utilise quatre niveaux de diagrammes, chacun offrant une perspective différente du système avec un niveau de détail croissant:

1. **Context (Contexte)** - Vue d'ensemble du système, montrant comment il s'intègre dans son environnement avec les utilisateurs et les systèmes externes.
2. **Container (Conteneur)** - Décomposition du système en conteneurs de haut niveau (applications, bases de données, interfaces utilisateur, etc.).
3. **Component (Composant)** - Décomposition de chaque conteneur en composants et leurs interactions.
4. **Code** - Implémentation détaillée des composants, généralement sous forme de diagrammes de classes.

## Structure de la Documentation

Notre documentation C4 Model est organisée comme suit:

- [**1. Diagramme de Contexte**](1_context.md) - Vue d'ensemble du système SODAV Monitor et de son environnement.
- [**2. Diagramme de Conteneurs**](2_containers.md) - Architecture de haut niveau du système SODAV Monitor.
- [**3. Diagrammes de Composants**](3_components/) - Décomposition détaillée de chaque conteneur:
  - [**3.1 Composants du Backend**](3_components/backend_components.md)
  - [**3.2 Composants du Frontend**](3_components/frontend_components.md)
  - [**3.3 Composants de Détection**](3_components/detection_components.md)
- [**4. Diagrammes de Code**](4_code/) - Implémentation détaillée des composants clés.

## Outils Utilisés

Pour créer et maintenir ces diagrammes, nous utilisons:

- [**Structurizr**](https://structurizr.com/) - Pour la création des diagrammes C4
- [**PlantUML**](https://plantuml.com/) - Pour les diagrammes de code
- [**Mermaid**](https://mermaid-js.github.io/) - Pour les diagrammes intégrés dans Markdown

## Comment Contribuer

Pour contribuer à cette documentation:

1. Familiarisez-vous avec le [C4 Model](https://c4model.com/)
2. Utilisez les outils mentionnés ci-dessus pour créer ou modifier les diagrammes
3. Suivez les conventions de nommage et de structure existantes
4. Soumettez vos modifications via une pull request

## Références

- [Site officiel du C4 Model](https://c4model.com/)
- [The C4 Model for Software Architecture](https://www.infoq.com/articles/C4-architecture-model/)
- [Visualising Software Architecture](https://leanpub.com/visualising-software-architecture)
