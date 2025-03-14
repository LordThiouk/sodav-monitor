# Updated Dockerfile with simplified dependencies
# Build stage for frontend
FROM node:18-alpine as frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Build stage for backend - using a more complete base image
FROM python:3.9-slim-buster

# Set working directory and environment
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PATH="/usr/local/bin:/root/.local/bin:${PATH}" \
    PORT=3000 \
    API_PORT=8000 \
    DEBUG=False \
    NODE_ENV=production

# Install minimal system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    nginx \
    ffmpeg \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/nginx /var/log/nginx /var/lib/nginx /var/cache/nginx /var/run/nginx \
    && mkdir -p /app/backend/logs && chmod 777 /app/backend/logs

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Install core dependencies
RUN pip install --no-cache-dir \
    uvicorn==0.22.0 \
    fastapi==0.95.2 \
    python-dotenv==1.0.0 \
    alembic==1.13.1 \
    SQLAlchemy==2.0.15 \
    psycopg2-binary==2.9.9 \
    websockets==12.0 \
    "python-jose[cryptography]==3.3.0" \
    "passlib[bcrypt]==1.7.4" \
    python-multipart==0.0.6 \
    pydub==0.25.1 \
    ffmpeg-python==0.2.0 \
    musicbrainzngs==0.7.1 \
    pyacoustid==1.2.0 \
    numpy==1.23.5 \
    scipy==1.11.0 \
    pandas==2.0.3 \
    numba==0.56.4 \
    librosa==0.10.0 \
    llvmlite==0.39.1 \
    aioredis>=2.0.0 \
    email-validator>=2.0.0 \
    requests>=2.31.0 \
    pydantic>=1.10.8 \
    av>=10.0.0 \
    redis>=5.0.1 \
    aiohttp>=3.9.1 \
    prometheus-client>=0.19.0 \
    typing-extensions>=4.5.0 \
    psutil>=5.9.0

# Copy backend files
COPY backend/ ./

# Créer le répertoire migrations s'il n'existe pas
RUN mkdir -p ./models/migrations

# Copier les migrations depuis le bon emplacement
COPY backend/models/migrations ./models/migrations/

# Définir les permissions
RUN chmod -R 755 ./models/migrations

# Copy frontend build and configuration files
COPY --from=frontend-build /app/frontend/build /app/frontend/build
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh && \
    sed -i 's/\r$//' /app/start.sh  # Fix line endings for Windows
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/default.conf /etc/nginx/conf.d/default.conf

# Expose ports
EXPOSE ${PORT} ${API_PORT}

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=60s --start-period=120s --retries=3 \
    CMD curl -f -H "X-Startup-Check: true" "http://localhost:${PORT}/api/health" || exit 1

# Start the application
WORKDIR /app
CMD ["./start.sh"]
