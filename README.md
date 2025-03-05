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

## Tests

### Tests Unitaires

Pour exécuter les tests unitaires :

```bash
python -m pytest backend/tests/ -v
```

### Tests d'Intégration

Nous avons ajouté une structure complète de tests d'intégration pour vérifier que les différents composants du système fonctionnent correctement ensemble. Ces tests sont organisés par composant :

```
backend/tests/integration/
├── api/                     # Tests d'intégration API
│   └── test_api_integration.py
├── detection/               # Tests d'intégration du système de détection
│   └── test_detection_integration.py
├── analytics/               # Tests d'intégration du système d'analytique
│   └── test_analytics_integration.py
├── conftest.py              # Fixtures partagées pour les tests d'intégration
└── README.md                # Documentation pour les tests d'intégration
```

Pour exécuter les tests d'intégration :

```bash
python -m pytest backend/tests/integration/ -v
```

### Scripts de Test

Nous avons ajouté des scripts pour faciliter l'exécution des tests et la génération de rapports de couverture :

- `scripts/run_integration_tests.sh` : Exécute tous les tests d'intégration et génère un rapport de couverture
- `scripts/run_all_tests.sh` : Exécute tous les tests (unitaires et d'intégration) et génère un rapport de couverture combiné

Pour exécuter ces scripts :

```bash
./scripts/run_integration_tests.sh
./scripts/run_all_tests.sh
```

### Documentation des Tests

Pour plus d'informations sur la stratégie de test, consultez les documents suivants :

- `docs/TESTING_STRATEGY.md` : Documentation détaillée sur la stratégie de test
- `docs/TESTS.md` : Documentation sur les tests existants et leur organisation
- `docs/INTEGRATION_TESTING.md` : Documentation spécifique pour les tests d'intégration
- `backend/tests/integration/README.md` : Documentation pour les tests d'intégration

## Intégration Continue (CI)

Nous avons configuré GitHub Actions pour exécuter automatiquement les tests à chaque push et pull request sur les branches `main` et `develop`. La configuration se trouve dans le fichier `.github/workflows/tests.yml`.

Le workflow CI exécute les étapes suivantes :

1. Configuration de l'environnement Python et Redis
2. Installation des dépendances
3. Exécution des tests unitaires avec génération de rapport de couverture
4. Exécution des tests d'intégration avec génération de rapport de couverture
5. Téléchargement des rapports de couverture vers Codecov

Pour visualiser les résultats des tests CI, consultez l'onglet "Actions" du dépôt GitHub.
