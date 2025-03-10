# Standards de Documentation pour SODAV Monitor

Ce document définit les standards de documentation à suivre pour le projet SODAV Monitor, afin d'assurer une documentation cohérente, complète et facile à maintenir.

## Principes Généraux

1. **Toute fonctionnalité doit être documentée** : Chaque module, classe, fonction et méthode doit avoir une documentation appropriée.
2. **La documentation doit être à jour** : La documentation doit être mise à jour en même temps que le code.
3. **La documentation doit être claire et concise** : Évitez le jargon inutile et les explications trop verbeuses.
4. **La documentation doit être accessible** : Utilisez un langage simple et des exemples concrets.

## Docstrings

Les docstrings sont des chaînes de documentation en Python qui sont utilisées pour documenter des modules, classes, fonctions et méthodes. Dans le projet SODAV Monitor, nous utilisons le style Google pour les docstrings.

### Format des Docstrings

```python
def fonction_exemple(param1: str, param2: int = 0) -> bool:
    """
    Description courte de la fonction.
    
    Description plus détaillée de la fonction sur plusieurs
    lignes si nécessaire.
    
    Args:
        param1: Description du premier paramètre.
        param2: Description du deuxième paramètre. Valeur par défaut: 0.
        
    Returns:
        Description de la valeur de retour.
        
    Raises:
        ValueError: Description de quand cette exception est levée.
        
    Examples:
        >>> fonction_exemple("test", 1)
        True
    """
    # Corps de la fonction
```

### Docstrings pour les Modules

Chaque module (fichier Python) doit commencer par une docstring qui décrit le but du module :

```python
"""
Module de détection musicale.

Ce module contient les fonctions et classes nécessaires pour détecter
les morceaux de musique dans un flux audio.
"""
```

### Docstrings pour les Classes

Les docstrings de classes doivent décrire le but de la classe et ses attributs :

```python
class TrackManager:
    """
    Gère les pistes musicales dans la base de données.
    
    Cette classe fournit des méthodes pour créer, rechercher et mettre à jour
    des pistes musicales dans la base de données.
    
    Attributes:
        db_session: Session de base de données SQLAlchemy.
        logger: Logger pour enregistrer les événements.
    """
```

### Docstrings pour les Fonctions et Méthodes

Les docstrings de fonctions et méthodes doivent décrire ce que fait la fonction, ses paramètres, sa valeur de retour et les exceptions qu'elle peut lever :

```python
def validate_isrc(isrc: str) -> bool:
    """
    Valide un code ISRC selon le format standard.
    
    Args:
        isrc: Code ISRC à valider.
        
    Returns:
        True si le format est valide, False sinon.
        
    Raises:
        TypeError: Si isrc n'est pas une chaîne de caractères.
    """
```

## Documentation avec Sphinx

Sphinx est un générateur de documentation qui peut convertir des docstrings en documentation HTML, PDF et autres formats. Pour le projet SODAV Monitor, nous utilisons Sphinx pour générer la documentation de l'API.

### Configuration de Sphinx

La configuration de Sphinx se trouve dans le dossier `docs/sphinx/`. Pour générer la documentation, exécutez :

```bash
cd docs/sphinx
make html
```

La documentation générée sera disponible dans `docs/sphinx/_build/html/`.

### Extensions Sphinx Utilisées

- **autodoc** : Génère la documentation à partir des docstrings.
- **napoleon** : Support du style Google pour les docstrings.
- **viewcode** : Ajoute des liens vers le code source.
- **intersphinx** : Permet de créer des liens vers d'autres documentations Sphinx.

### Organisation de la Documentation

La documentation est organisée en sections :

1. **Guide d'Installation** : Instructions pour installer et configurer le projet.
2. **Guide d'Utilisation** : Comment utiliser les différentes fonctionnalités du projet.
3. **Référence de l'API** : Documentation générée à partir des docstrings.
4. **Guide de Contribution** : Comment contribuer au projet.
5. **Changelog** : Historique des modifications.

## Documentation des Fichiers README

Chaque dossier principal doit contenir un fichier `README.md` qui explique le but du dossier et son contenu. Le fichier README principal du projet doit contenir :

1. **Description du Projet** : Une brève description du projet SODAV Monitor.
2. **Installation** : Instructions d'installation.
3. **Utilisation** : Comment utiliser le projet.
4. **Structure du Projet** : Organisation des fichiers et dossiers.
5. **Contribution** : Comment contribuer au projet.
6. **Licence** : Informations sur la licence.

## Documentation des Changements

Tous les changements significatifs doivent être documentés dans le fichier `CHANGELOG.md` à la racine du projet. Le format du changelog doit suivre le [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

## Documentation des Tests

Les tests doivent également être documentés. Chaque test doit avoir une docstring qui explique ce qu'il teste et comment il le teste.

```python
def test_validate_isrc():
    """
    Teste la fonction validate_isrc avec différents codes ISRC.
    
    Vérifie que la fonction retourne True pour les ISRC valides
    et False pour les ISRC invalides.
    """
```

## Documentation des Scripts

Les scripts utilitaires doivent être documentés avec des docstrings et des commentaires. Ils doivent également avoir une section d'aide accessible via l'option `--help`.

## Mise à Jour de la Documentation

La documentation doit être mise à jour en même temps que le code. Avant de soumettre un pull request, assurez-vous que :

1. Toutes les nouvelles fonctionnalités sont documentées.
2. Les docstrings sont à jour.
3. La documentation générée par Sphinx est à jour.
4. Le changelog est mis à jour si nécessaire.

## Bonnes Pratiques

1. **Utilisez des exemples** : Les exemples aident à comprendre comment utiliser une fonction ou une classe.
2. **Documentez les cas d'erreur** : Expliquez quand et pourquoi des exceptions peuvent être levées.
3. **Utilisez des annotations de type** : Les annotations de type aident à comprendre les types attendus pour les paramètres et les valeurs de retour.
4. **Soyez cohérent** : Utilisez le même style de documentation dans tout le projet.
5. **Évitez la duplication** : Ne répétez pas les informations qui sont déjà disponibles ailleurs.

## Exemple Complet

Voici un exemple complet de documentation pour un module du projet SODAV Monitor :

```python
"""
Module de validation des codes ISRC.

Ce module contient des fonctions pour valider et normaliser les codes ISRC
(International Standard Recording Code) utilisés pour identifier de manière
unique les enregistrements sonores.
"""

from typing import Tuple, Optional
import re
import logging

logger = logging.getLogger(__name__)

def validate_isrc(isrc: str) -> Tuple[bool, Optional[str]]:
    """
    Valide et normalise un code ISRC.
    
    Format ISRC: CC-XXX-YY-NNNNN
    - CC: Code pays (2 lettres)
    - XXX: Code du propriétaire (3 caractères alphanumériques)
    - YY: Année de référence (2 chiffres)
    - NNNNN: Code de désignation (5 chiffres)
    
    Args:
        isrc: Code ISRC à valider.
        
    Returns:
        Tuple contenant:
        - Un booléen indiquant si l'ISRC est valide.
        - L'ISRC normalisé si valide, None sinon.
        
    Examples:
        >>> validate_isrc("FR-Z03-14-00123")
        (True, "FRZ0314000123")
        >>> validate_isrc("XX-123-45-6789")
        (False, None)
    """
    if not isrc or not isinstance(isrc, str):
        logger.warning(f"ISRC invalide (type incorrect ou vide): {isrc}")
        return False, None
    
    # Supprimer les tirets et les espaces, mettre en majuscules
    normalized_isrc = re.sub(r'[\s-]', '', isrc).upper()
    
    # Vérifier la longueur
    if len(normalized_isrc) != 12:
        logger.warning(f"ISRC invalide (longueur incorrecte): {isrc} -> {normalized_isrc}")
        return False, None
    
    # Vérifier le format
    pattern = r'^[A-Z]{2}[A-Z0-9]{3}[0-9]{7}$'
    if not re.match(pattern, normalized_isrc):
        logger.warning(f"ISRC invalide (format incorrect): {isrc} -> {normalized_isrc}")
        return False, None
    
    return True, normalized_isrc
```

## Ressources

- [Guide de Style Google pour Python](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [Documentation Sphinx](https://www.sphinx-doc.org/en/master/)
- [Extension Napoleon pour Sphinx](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
- [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/) 