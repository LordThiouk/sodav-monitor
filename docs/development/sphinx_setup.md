# Configuration de Sphinx pour SODAV Monitor

Ce guide explique comment configurer et utiliser Sphinx pour générer la documentation du projet SODAV Monitor à partir des docstrings.

## Prérequis

Avant de commencer, assurez-vous d'avoir installé les packages nécessaires :

```bash
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints
```

## Structure des Dossiers

Créez la structure de dossiers suivante pour la documentation Sphinx :

```
docs/
└── sphinx/
    ├── source/
    │   ├── _static/
    │   ├── _templates/
    │   ├── api/
    │   ├── guides/
    │   ├── conf.py
    │   ├── index.rst
    │   └── ...
    ├── Makefile
    └── make.bat
```

## Initialisation de Sphinx

Pour initialiser Sphinx, exécutez les commandes suivantes :

```bash
mkdir -p docs/sphinx
cd docs/sphinx
sphinx-quickstart
```

Répondez aux questions comme suit :
- Séparer les répertoires source et build : Oui
- Nom du projet : SODAV Monitor
- Auteur(s) : Votre nom
- Version du projet : 1.0.0
- Langage du projet : fr

## Configuration de Sphinx

Modifiez le fichier `docs/sphinx/source/conf.py` pour configurer Sphinx :

```python
# Configuration file for the Sphinx documentation builder.
import os
import sys
import datetime

# Ajouter le répertoire racine du projet au chemin Python
sys.path.insert(0, os.path.abspath('../../..'))

# -- Project information -----------------------------------------------------
project = 'SODAV Monitor'
copyright = f'{datetime.datetime.now().year}, SODAV'
author = 'Équipe SODAV Monitor'
version = '1.0.0'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosummary',
    'sphinx_autodoc_typehints',
]

templates_path = ['_templates']
exclude_patterns = []
language = 'fr'

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True
napoleon_type_aliases = None
napoleon_attr_annotations = True

# -- Options for intersphinx extension ---------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'sqlalchemy': ('https://docs.sqlalchemy.org/en/14/', None),
    'fastapi': ('https://fastapi.tiangolo.com/', None),
}
```

## Création des Fichiers de Documentation

### Fichier Index Principal

Créez le fichier `docs/sphinx/source/index.rst` :

```rst
Documentation SODAV Monitor
===========================

SODAV Monitor est un système de monitoring automatisé pour les chaînes de radio et de télévision sénégalaises, conçu pour la SODAV (Société Sénégalaise du Droit d'Auteur et des Droits Voisins).

.. toctree::
   :maxdepth: 2
   :caption: Contenu:

   guides/installation
   guides/utilisation
   guides/configuration
   api/index
   guides/contribution
   guides/changelog

Indices et tables
================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
```

### Documentation de l'API

Créez le fichier `docs/sphinx/source/api/index.rst` :

```rst
Référence de l'API
=================

Cette section contient la documentation générée automatiquement à partir des docstrings du code source.

.. toctree::
   :maxdepth: 2

   detection
   models
   utils
```

Créez le fichier `docs/sphinx/source/api/detection.rst` :

```rst
Module de Détection
==================

.. automodule:: backend.detection
   :members:
   :undoc-members:
   :show-inheritance:

Sous-modules
-----------

.. toctree::
   :maxdepth: 1

   detection/audio_processor
```

Créez le fichier `docs/sphinx/source/api/detection/audio_processor.rst` :

```rst
Module de Traitement Audio
========================

.. automodule:: backend.detection.audio_processor
   :members:
   :undoc-members:
   :show-inheritance:

Sous-modules
-----------

.. toctree::
   :maxdepth: 1

   audio_processor/external_services
   audio_processor/track_manager
```

Créez des fichiers similaires pour les autres modules du projet.

## Génération de la Documentation

Pour générer la documentation, exécutez les commandes suivantes :

```bash
cd docs/sphinx
make html
```

La documentation générée sera disponible dans `docs/sphinx/build/html/`.

## Intégration Continue

Pour générer automatiquement la documentation à chaque push, vous pouvez ajouter une étape dans votre pipeline CI/CD :

```yaml
# .github/workflows/docs.yml
name: Documentation

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints
    - name: Build documentation
      run: |
        cd docs/sphinx
        make html
    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      if: github.event_name == 'push' && github.ref == 'refs/heads/main'
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./docs/sphinx/build/html
```

## Bonnes Pratiques

1. **Mettez à jour la documentation régulièrement** : Générez la documentation après chaque modification significative du code.
2. **Vérifiez les avertissements** : Sphinx génère des avertissements lorsqu'il rencontre des problèmes dans la documentation. Corrigez-les pour améliorer la qualité de la documentation.
3. **Utilisez des références croisées** : Utilisez des références croisées pour lier les différentes parties de la documentation.
4. **Incluez des exemples** : Les exemples aident à comprendre comment utiliser les fonctionnalités.
5. **Documentez les exceptions** : Documentez les exceptions qui peuvent être levées par les fonctions et méthodes.

## Ressources

- [Documentation Sphinx](https://www.sphinx-doc.org/en/master/)
- [Sphinx reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [Extension Napoleon pour Sphinx](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
- [Thème Read the Docs pour Sphinx](https://sphinx-rtd-theme.readthedocs.io/en/stable/)
