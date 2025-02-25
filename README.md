# SODAV Monitor

Un système de monitoring automatisé pour les chaînes de radio et de télévision sénégalaises, conçu pour la SODAV (Société Sénégalaise du Droit d'Auteur et des Droits Voisins).

## 🎯 Objectifs

- Surveillance en temps réel des flux audio et vidéo
- Détection et identification des morceaux de musique diffusés en direct
- Génération de rapports de diffusion précis pour améliorer la distribution des droits d'auteur
- Alternative rentable et évolutive aux solutions existantes
- Exploitation des technologies cloud, IA et Big Data pour un traitement efficace

## 📂 Structure du Projet

```
/sodav_monitor/
│
├── backend/
│   ├── detection/              # Logique de détection musicale
│   │   ├── audio_fingerprint.py
│   │   ├── audio_processor.py
│   │   ├── detect_music.py
│   │   ├── fingerprint.py
│   │   └── music_recognition.py
│   │
│   ├── processing/            # Traitement des données
│   │   └── radio_manager.py
│   │
│   ├── reports/              # Gestion des rapports
│   │
│   ├── logs/                 # Gestion des logs
│   │
│   ├── analytics/            # Données analytiques
│   │
│   ├── models/              # Modèles de la base de données
│   │   ├── models.py
│   │   └── database.py
│   │
│   ├── utils/               # Fonctions utilitaires
│   │   ├── config.py
│   │   └── redis_config.py
│   │
│   └── tests/               # Tests unitaires
│
├── frontend/               # Interface utilisateur React/Next.js
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── theme/
│   │   └── utils/
│   │
│   └── public/
│
├── docker/                # Configuration Docker
│   ├── Dockerfile
│   ├── nginx.conf
│   └── default.conf
│
├── scripts/              # Scripts utilitaires
│   └── reorganize.py
│
├── requirements.txt      # Dépendances Python
└── .env.example         # Template des variables d'environnement
```

## 🚀 Installation

1. Cloner le repository :
```bash
git clone https://github.com/votre-org/sodav-monitor.git
cd sodav-monitor
```

2. Créer et activer un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Configurer les variables d'environnement :
```bash
cp .env.example .env
# Éditer .env avec vos configurations
```

5. Lancer l'application :
```bash
# En développement
python backend/main.py

# Avec Docker
docker-compose up
```

## 🛠 Technologies Utilisées

- **Backend** : Python, FastAPI
- **Frontend** : React, Next.js
- **Base de données** : PostgreSQL, Redis
- **Conteneurisation** : Docker
- **Détection Audio** : Chromaprint, AcoustID
- **Cloud** : AWS/GCP (selon le déploiement)

## 📊 Fonctionnalités

- Détection en temps réel des morceaux de musique
- Interface de monitoring en direct
- Génération de rapports détaillés
- Gestion des droits d'auteur
- Analyses statistiques
- API RESTful

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Forker le projet
2. Créer une branche pour votre fonctionnalité
3. Commiter vos changements
4. Pousser vers la branche
5. Ouvrir une Pull Request

## 📝 Licence

Ce projet est sous licence [À définir] - voir le fichier LICENSE pour plus de détails.

## 👥 Contact

Pour toute question ou suggestion, n'hésitez pas à nous contacter :
- Email : [À définir]
- Site web : [À définir]
