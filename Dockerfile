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

# Exposer le port pour Railway
EXPOSE 8000

# Commande de démarrage (utilisant directement uvicorn sans shell)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 