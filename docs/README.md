# Documentation SODAV Monitor

Ce dossier contient toute la documentation du projet SODAV Monitor.

## Structure de la Documentation

La documentation est organisée en plusieurs sections thématiques :

- **[architecture/](architecture/)** : Architecture globale du système, diagrammes et décisions de conception
- **[api/](api/)** : Documentation de l'API REST et des intégrations externes
- **[database/](database/)** : Schéma de base de données, migrations et gestion des données
- **[detection/](detection/)** : Système de détection musicale, algorithmes et optimisations
- **[development/](development/)** : Guides de développement, standards de code et contribution
- **[security/](security/)** : Directives de sécurité et bonnes pratiques
- **[performance/](performance/)** : Tests de performance et optimisations
- **[tests/](tests/)** : Documentation des tests et stratégies de test
- **[sphinx/](sphinx/)** : Documentation générée automatiquement avec Sphinx

## Documentation Générée

La documentation de l'API est générée automatiquement à partir des docstrings du code source à l'aide de Sphinx. Pour générer la documentation :

```bash
# Installer les dépendances nécessaires
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints

# Générer la documentation
cd docs/sphinx
make html
```

La documentation générée sera disponible dans `docs/sphinx/build/html/`.

## Standards de Documentation

Toutes les fonctions, classes et méthodes doivent être documentées avec des docstrings au format Google. Pour plus d'informations sur les standards de documentation, consultez [development/documentation_standards.md](development/documentation_standards.md).

## Contribution à la Documentation

Pour contribuer à la documentation :

1. Assurez-vous que votre documentation suit les standards définis
2. Placez votre documentation dans le dossier thématique approprié
3. Mettez à jour le fichier README.md du dossier concerné
4. Si nécessaire, mettez à jour le fichier README.md principal 