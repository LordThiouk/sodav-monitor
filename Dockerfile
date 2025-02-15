# Utiliser une image Python stable
FROM python:3.12

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers du projet
COPY . /app/

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python avec un environnement propre
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port pour Railway
EXPOSE 8000

# Commande de démarrage (ajustée pour le chemin backend)
CMD ["sh", "-c", "cd backend && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"] 