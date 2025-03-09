#!/bin/bash
# Script pour démarrer l'application dans différents environnements

# Vérifier si l'environnement est spécifié
if [ -z "$1" ]; then
    echo "Usage: $0 [development|production]"
    echo "Example: $0 development"
    exit 1
fi

ENV=$1

# Aller au répertoire racine du projet
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Vérifier si le fichier .env.{ENV} existe
if [ ! -f ".env.$ENV" ]; then
    echo "Erreur: Le fichier .env.$ENV n'existe pas."
    echo "Veuillez créer ce fichier en vous basant sur .env.example"
    exit 1
fi

# Exporter la variable d'environnement ENV
export ENV=$ENV

echo "Démarrage de l'application en environnement $ENV..."
echo "Utilisation du fichier de configuration: .env.$ENV"

# Créer les répertoires nécessaires s'ils n'existent pas
mkdir -p backend/logs
mkdir -p backend/reports
mkdir -p backend/data

echo "Vérification des répertoires nécessaires terminée."

# Démarrer l'application
if [ "$ENV" = "development" ]; then
    # Mode développement avec rechargement automatique
    echo "Mode développement avec rechargement automatique"
    python backend/run_app.py
else
    # Mode production
    echo "Mode production"
    python backend/run.py
fi 