# Utiliser une image Python stable et légère
FROM python:3.12-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    python3-distutils \
    python3-pip \
    gcc \
    libpq-dev \
    ffmpeg \
    libsndfile1 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Mettre à jour pip avant d'installer les dépendances
RUN pip install --upgrade pip setuptools wheel

# Copier uniquement le fichier des dépendances pour un build plus rapide
COPY requirements.txt /app/

# Installer les dépendances sans cache
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste des fichiers du projet
COPY . /app/

# S'assurer que tous les fichiers ont les bonnes permissions
RUN chmod -R 755 /app

# Définir le répertoire de travail pour le backend
WORKDIR /app/backend

# Script de démarrage pour gérer le port et les vérifications
COPY <<EOF /app/start.sh
#!/bin/bash
export PORT=\${PORT:-8000}
echo "Starting application on port \$PORT"

# Attendre que PostgreSQL soit prêt
until curl -s "\$DATABASE_URL" >/dev/null 2>&1; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

# Démarrer l'application
exec uvicorn main:app --host 0.0.0.0 --port \$PORT
EOF

RUN chmod +x /app/start.sh

# Exposer le port pour Railway
EXPOSE 8000

# Commande de démarrage
CMD ["/app/start.sh"] 