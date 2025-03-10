# SODAV Monitor

Un système de monitoring automatisé pour les chaînes de radio et de télévision sénégalaises, conçu pour la SODAV (Société Sénégalaise du Droit d'Auteur et des Droits Voisins).

## 🎯 Objectifs

- Surveillance en temps réel des flux audio et vidéo
- Détection et identification des morceaux de musique diffusés en direct
- Génération de rapports de diffusion précis pour améliorer la distribution des droits d'auteur
- Alternative rentable et évolutive aux solutions existantes
- Exploitation des technologies cloud, IA et Big Data pour un traitement efficace

## 📝 Logs et Monitoring

Les logs de l'application sont centralisés dans le dossier `backend/logs/` :
- `sodav.log` : Logs généraux de l'application
- `error.log` : Logs d'erreurs uniquement

Note : Le dossier `logs` à la racine du projet est déprécié. Tous les logs doivent être stockés dans `backend/logs/`.

### Monitoring

Le système SODAV Monitor propose deux options de monitoring :

1. **Monitoring avec Prometheus et Grafana** : Solution complète de monitoring nécessitant Docker. Pour plus d'informations, consultez [docs/performance/monitoring.md](docs/performance/monitoring.md).

2. **Monitoring Intégré dans le Frontend** : Solution légère de monitoring intégrée directement dans l'interface utilisateur, ne nécessitant pas Docker. Pour plus d'informations, consultez [docs/performance/frontend_monitoring.md](docs/performance/frontend_monitoring.md).

Pour accéder au monitoring intégré dans le frontend, connectez-vous à l'application et cliquez sur "Monitoring" dans la barre de navigation.

## 🔒 Sécurité

La sécurité est une priorité pour le projet SODAV Monitor. Veuillez suivre ces directives :

- **Variables d'environnement** : Toutes les données sensibles (mots de passe, clés API, etc.) doivent être stockées dans des variables d'environnement via un fichier `.env` qui n'est jamais commité.
- **Configuration** : Utilisez le fichier `.env.example` comme modèle pour créer votre propre fichier `.env`.
- **Railway** : Pour le déploiement sur Railway, utilisez `railway.json.example` comme modèle et configurez les secrets via la plateforme Railway.
- **Scripts** : Pour les scripts nécessitant des identifiants, utilisez les variables d'environnement `ADMIN_EMAIL` et `ADMIN_PASSWORD`.

Pour plus d'informations sur les bonnes pratiques de sécurité, consultez [docs/SECURITY_GUIDELINES.md](docs/SECURITY_GUIDELINES.md).

## 🌍 Gestion des Environnements

Le projet SODAV Monitor prend en charge plusieurs environnements de déploiement :

### Configuration des Environnements

1. **Fichiers de Configuration**
   - `.env.development` : Configuration pour l'environnement de développement
   - `.env.production` : Configuration pour l'environnement de production
   - `.env.example` : Modèle pour créer vos propres fichiers de configuration

2. **Création des Fichiers de Configuration**
   ```bash
   # Pour le développement
   cp .env.example .env.development
   # Éditez .env.development avec vos configurations de développement
   
   # Pour la production
   cp .env.example .env.production
   # Éditez .env.production avec vos configurations de production
   ```

3. **Démarrage de l'Application**
   ```bash
   # Pour Windows (PowerShell)
   # Pour le développement
   .\backend\scripts\startup\start_env.ps1 development
   
   # Pour la production
   .\backend\scripts\startup\start_env.ps1 production
   
   # Pour Linux/Mac (Bash)
   # Pour le développement
   ./backend/scripts/startup/start_env.sh development
   
   # Pour la production
   ./backend/scripts/startup/start_env.sh production
   ```

4. **Organisation des Fichiers**
   - **Logs** : Les logs sont stockés dans `backend/logs/`
   - **Rapports** : Les rapports générés sont stockés dans `backend/reports/`
   - **Données** : Les données de l'application sont stockées dans `backend/data/`
   - **Scripts** : Les scripts utilitaires sont dans `backend/scripts/` (organisés par catégorie)

5. **Variables Spécifiques à l'Environnement**
   - Base de données : Utilisez des bases de données différentes pour le développement et la production
   - Redis : Configurez des instances Redis séparées pour chaque environnement
   - Clés API : Utilisez des clés API distinctes pour le développement et la production
   - Logs : Utilisez un niveau de log plus détaillé (DEBUG) en développement

Pour plus de détails sur les configurations spécifiques à chaque environnement, consultez les commentaires dans le fichier `.env.example`.

## 📂 Structure du Projet

Pour plus de détails sur l'organisation du projet et les changements structurels récents, consultez [docs/architecture/reorganisation.md](docs/architecture/reorganisation.md).

## 📚 Documentation

La documentation du projet SODAV Monitor est organisée de manière thématique dans le dossier `docs/`. Un index complet est disponible dans [docs/index.md](docs/index.md).

### Structure de la Documentation

- **[Architecture](docs/architecture/)** : Architecture globale du système, diagrammes et décisions de conception
- **[API](docs/api/)** : Documentation de l'API REST et des intégrations externes
- **[Base de Données](docs/database/)** : Schéma de base de données, migrations et gestion des données
- **[Détection](docs/detection/)** : Système de détection musicale, algorithmes et optimisations
- **[Développement](docs/development/)** : Guides de développement, standards de code et contribution
- **[Sécurité](docs/security/)** : Directives de sécurité et bonnes pratiques
- **[Performance](docs/performance/)** : Tests de performance et optimisations
- **[Tests](docs/tests/)** : Documentation des tests et stratégies de test
- **[Résolution des Problèmes](docs/troubleshooting/)** : Guide de résolution des problèmes courants

### Documentation Générée

La documentation de l'API est générée automatiquement à partir des docstrings du code source à l'aide de Sphinx. Pour générer la documentation :

```bash
# Installer les dépendances nécessaires
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints

# Générer la documentation
cd docs/sphinx
make html
```

La documentation générée sera disponible dans `docs/sphinx/build/html/`.

Pour plus d'informations sur la configuration de Sphinx, consultez [docs/development/sphinx_setup.md](docs/development/sphinx_setup.md).

### Standards de Documentation

Toutes les fonctions, classes et méthodes doivent être documentées avec des docstrings au format Google. Pour plus d'informations sur les standards de documentation, consultez [docs/development/documentation_standards.md](docs/development/documentation_standards.md).

### Contrainte d'Unicité ISRC

Le système utilise une contrainte d'unicité sur les codes ISRC pour éviter les doublons de pistes dans la base de données. Pour plus d'informations, consultez :
- [docs/database/migrations/isrc_unique_constraint.md](docs/database/migrations/isrc_unique_constraint.md)
- [docs/tests/isrc_uniqueness_test.md](docs/tests/isrc_uniqueness_test.md)
- [docs/detection/isrc_best_practices.md](docs/detection/isrc_best_practices.md)

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
cp .env.example .env.development
# Éditer .env.development avec vos configurations
```

5. Lancer l'application :
```bash
# En développement
.\backend\scripts\startup\start_env.ps1 development  # Windows
./backend/scripts/startup/start_env.sh development   # Linux/Mac

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

```bash
# Exécuter tous les tests
python -m backend.scripts.tests.run_tests

# Exécuter les tests d'intégration
./backend/scripts/tests/run_integration_tests.sh

# Exécuter tous les tests avec rapport de couverture
./backend/scripts/tests/run_all_tests.sh
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

