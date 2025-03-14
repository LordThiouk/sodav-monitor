Guide d'Installation
==================

Prérequis
--------

* Python 3.8 ou supérieur
* PostgreSQL 12 ou supérieur
* Node.js 14 ou supérieur (pour le frontend)

Installation du Backend
---------------------

1. Cloner le dépôt :

.. code-block:: bash

   git clone https://github.com/sodav/sodav-monitor.git
   cd sodav-monitor

2. Créer un environnement virtuel :

.. code-block:: bash

   python -m venv venv
   source venv/bin/activate  # Sur Windows : venv\Scripts\activate

3. Installer les dépendances :

.. code-block:: bash

   pip install -r requirements.txt

4. Configurer les variables d'environnement :

Créez un fichier `.env` à la racine du projet avec les variables suivantes :

.. code-block:: bash

   DATABASE_URL=postgresql://user:password@localhost/sodav_monitor
   ACOUSTID_API_KEY=votre_cle_acoustid
   AUDD_API_KEY=votre_cle_audd
   SECRET_KEY=votre_cle_secrete
   ENVIRONMENT=development

5. Initialiser la base de données :

.. code-block:: bash

   python -m backend.models.database init_db

Installation du Frontend
----------------------

1. Naviguer vers le dossier frontend :

.. code-block:: bash

   cd frontend

2. Installer les dépendances :

.. code-block:: bash

   npm install

3. Créer un fichier `.env.local` avec les variables suivantes :

.. code-block:: bash

   NEXT_PUBLIC_API_URL=http://localhost:8000

Lancement de l'Application
------------------------

1. Lancer le backend :

.. code-block:: bash

   python -m backend.main

2. Lancer le frontend (dans un autre terminal) :

.. code-block:: bash

   cd frontend
   npm run dev

L'application sera accessible à l'adresse http://localhost:3000.
