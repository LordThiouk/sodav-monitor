Guide de Configuration
====================

Cette section explique comment configurer les différents aspects de SODAV Monitor.

Configuration de l'Environnement
------------------------------

SODAV Monitor utilise des variables d'environnement pour sa configuration. Ces variables peuvent être définies dans un fichier `.env` à la racine du projet.

Variables d'Environnement Principales
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Configuration de la base de données
   DATABASE_URL=postgresql://user:password@localhost/sodav_monitor
   
   # Clés API pour les services de détection
   ACOUSTID_API_KEY=votre_cle_acoustid
   AUDD_API_KEY=votre_cle_audd
   
   # Configuration de sécurité
   SECRET_KEY=votre_cle_secrete
   
   # Environnement (development, testing, production)
   ENVIRONMENT=development
   
   # Configuration du serveur
   HOST=0.0.0.0
   PORT=8000
   
   # Configuration des logs
   LOG_LEVEL=INFO
   LOG_DIR=backend/logs

Configuration de la Base de Données
--------------------------------

La base de données est configurée via la variable d'environnement `DATABASE_URL`. Le format est le suivant :

.. code-block:: bash

   DATABASE_URL=postgresql://utilisateur:mot_de_passe@hote:port/nom_base

Pour configurer manuellement la base de données, modifiez le fichier `backend/models/database.py`.

Configuration des Services de Détection
------------------------------------

SODAV Monitor utilise plusieurs services pour la détection musicale :

1. **AcoustID** : Service de reconnaissance musicale basé sur les empreintes acoustiques
2. **AudD** : Service de reconnaissance musicale basé sur l'audio

Pour configurer ces services, vous devez obtenir des clés API et les définir dans les variables d'environnement.

Configuration des Stations Radio
-----------------------------

Les stations radio peuvent être configurées via l'interface web ou directement dans la base de données.

Pour ajouter une station via l'API :

.. code-block:: bash

   curl -X POST "http://localhost:8000/api/stations" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer votre_token" \
     -d '{
       "name": "Nom de la Station",
       "stream_url": "http://exemple.com/stream",
       "country": "SN",
       "language": "fr",
       "is_active": true
     }'

Configuration des Rapports
-----------------------

Les rapports peuvent être configurés via l'interface web ou l'API. Vous pouvez définir :

- Types de rapports disponibles
- Formats de sortie
- Modèles de rapports
- Planification des rapports automatiques

Pour configurer les modèles de rapports, modifiez les fichiers dans le dossier `backend/reports/templates/`.

Configuration des Notifications
----------------------------

SODAV Monitor peut envoyer des notifications par email. Pour configurer le service d'email :

.. code-block:: bash

   # Configuration SMTP
   SMTP_SERVER=smtp.example.com
   SMTP_PORT=587
   SMTP_USERNAME=votre_email@example.com
   SMTP_PASSWORD=votre_mot_de_passe
   SMTP_FROM=noreply@sodav.sn

Configuration des Performances
---------------------------

Pour optimiser les performances, vous pouvez ajuster les paramètres suivants :

.. code-block:: bash

   # Nombre de workers pour le serveur
   WORKERS=4
   
   # Taille du pool de connexions à la base de données
   DB_POOL_SIZE=20
   
   # Intervalle de détection (en secondes)
   DETECTION_INTERVAL=30
   
   # Taille maximale des fichiers audio (en Mo)
   MAX_AUDIO_SIZE=10

Configuration du Frontend
----------------------

Le frontend peut être configuré via le fichier `.env.local` dans le dossier `frontend` :

.. code-block:: bash

   # URL de l'API backend
   NEXT_PUBLIC_API_URL=http://localhost:8000
   
   # Intervalle de rafraîchissement des données (en ms)
   NEXT_PUBLIC_REFRESH_INTERVAL=5000
   
   # Langue par défaut
   NEXT_PUBLIC_DEFAULT_LOCALE=fr 