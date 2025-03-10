Guide de Contribution
===================

Cette section explique comment contribuer au projet SODAV Monitor.

Prérequis
--------

Avant de commencer à contribuer, assurez-vous d'avoir :

* Un compte GitHub
* Git installé sur votre machine
* Python 3.8 ou supérieur
* PostgreSQL 12 ou supérieur
* Node.js 14 ou supérieur (pour le frontend)

Processus de Contribution
-----------------------

1. **Fork du dépôt** : Créez un fork du dépôt principal sur GitHub.

2. **Clone du dépôt** : Clonez votre fork sur votre machine locale.

   .. code-block:: bash

      git clone https://github.com/votre-username/sodav-monitor.git
      cd sodav-monitor

3. **Création d'une branche** : Créez une branche pour votre contribution.

   .. code-block:: bash

      git checkout -b feature/nom-de-votre-feature

4. **Développement** : Effectuez vos modifications en suivant les standards de code.

5. **Tests** : Assurez-vous que tous les tests passent.

   .. code-block:: bash

      python -m pytest

6. **Commit** : Committez vos changements avec un message descriptif.

   .. code-block:: bash

      git add .
      git commit -m "Description claire de vos changements"

7. **Push** : Poussez vos changements vers votre fork.

   .. code-block:: bash

      git push origin feature/nom-de-votre-feature

8. **Pull Request** : Créez une Pull Request depuis votre fork vers le dépôt principal.

Standards de Code
--------------

### Python

* Suivez la PEP 8 pour le style de code
* Utilisez des docstrings au format Google pour documenter les fonctions et classes
* Ajoutez des annotations de type
* Maintenez une couverture de tests d'au moins 90%

### TypeScript/React

* Utilisez ESLint et Prettier pour le formatage
* Suivez les principes de React Hooks
* Utilisez TypeScript pour le typage statique
* Organisez les composants de manière modulaire

Documentation
-----------

Toute nouvelle fonctionnalité doit être documentée :

1. **Docstrings** : Ajoutez des docstrings à toutes les fonctions, classes et méthodes.
2. **Documentation Sphinx** : Mettez à jour la documentation Sphinx si nécessaire.
3. **README** : Mettez à jour le README si votre contribution change l'utilisation du projet.

Exemple de docstring :

.. code-block:: python

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

Tests
----

Chaque contribution doit être accompagnée de tests :

1. **Tests unitaires** : Testez les fonctions et méthodes individuelles.
2. **Tests d'intégration** : Testez l'interaction entre les composants.
3. **Tests de bout en bout** : Testez les flux complets si nécessaire.

Exemple de test :

.. code-block:: python

   def test_validate_isrc():
       """Teste la fonction validate_isrc avec différents cas."""
       # Cas valide
       is_valid, normalized = validate_isrc("FR-Z03-14-00123")
       assert is_valid is True
       assert normalized == "FRZ0314000123"
       
       # Cas invalide
       is_valid, normalized = validate_isrc("XX-123-45-6789")
       assert is_valid is False
       assert normalized is None

Soumission de Bugs
---------------

Si vous trouvez un bug, veuillez créer une issue sur GitHub avec les informations suivantes :

1. **Titre** : Description concise du problème
2. **Description** : Explication détaillée du problème
3. **Étapes pour reproduire** : Comment reproduire le bug
4. **Comportement attendu** : Ce qui devrait se passer
5. **Comportement actuel** : Ce qui se passe réellement
6. **Environnement** : Informations sur votre environnement (OS, version de Python, etc.)
7. **Logs** : Logs pertinents si disponibles

Propositions de Fonctionnalités
----------------------------

Pour proposer une nouvelle fonctionnalité, créez une issue sur GitHub avec les informations suivantes :

1. **Titre** : Nom de la fonctionnalité
2. **Description** : Explication détaillée de la fonctionnalité
3. **Cas d'utilisation** : Comment cette fonctionnalité sera utilisée
4. **Bénéfices** : Pourquoi cette fonctionnalité est utile
5. **Alternatives** : Autres approches envisagées
6. **Maquettes** : Maquettes ou diagrammes si pertinent 