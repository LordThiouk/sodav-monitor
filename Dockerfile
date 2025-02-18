# Updated Dockerfile to trigger rebuild - v2
# Build stage for frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Build stage for backend
FROM python:3.9.18-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    libopenal1 \
    python3-dev \
    ffmpeg \
    curl \
    nginx \
    gettext-base \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    procps \
    libsndfile1 \
    libsndfile1-dev \
    libportaudio2 \
    portaudio19-dev \
    python3-scipy \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/nginx \
    && mkdir -p /var/log/nginx \
    && mkdir -p /var/lib/nginx \
    && chown -R www-data:www-data /run/nginx \
    && chown -R www-data:www-data /var/log/nginx \
    && chown -R www-data:www-data /var/lib/nginx

# Set working directory
WORKDIR /app/backend

# Update pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY backend/requirements.txt ./

# Install scientific computing dependencies first
RUN pip install --no-cache-dir \
    numpy>=1.23.5 \
    scipy>=1.11.0 \
    pandas>=2.0.3

# Install all Python dependencies with retry mechanism
RUN for i in {1..3}; do \
    pip install --no-cache-dir \
    python-dotenv>=1.0.0 \
    alembic>=1.13.1 \
    psycopg2-binary>=2.9.9 \
    SQLAlchemy>=2.0.15 \
    uvicorn>=0.22.0 \
    fastapi>=0.95.2 \
    websockets>=12.0 \
    python-jose[cryptography]>=3.3.0 \
    passlib[bcrypt]>=1.7.4 \
    aioredis>=2.0.0 \
    python-multipart>=0.0.6 \
    email-validator>=2.0.0 \
    requests>=2.31.0 \
    pydantic>=1.10.8 \
    librosa>=0.10.0 \
    pydub>=0.25.1 \
    ffmpeg-python>=0.2.0 \
    musicbrainzngs>=0.7.1 \
    pyacoustid>=1.2.0 \
    av>=10.0.0 \
    redis>=5.0.1 \
    aiohttp>=3.9.1 \
    prometheus-client>=0.19.0 \
    typing-extensions>=4.5.0 \
    psutil>=5.9.0 \
    -r requirements.txt && break || sleep 2; \
    done

# Install Alembic globally and ensure it's in PATH
RUN pip install --no-cache-dir alembic>=1.13.1 && \
    ln -sf $(which alembic) /usr/local/bin/alembic && \
    chmod +x /usr/local/bin/alembic

# Copy backend files with explicit handling of migrations
COPY backend/ ./
COPY backend/migrations ./migrations/
RUN chmod -R 755 migrations

# Copy frontend build from build stage
COPY --from=frontend-build /app/frontend/build /app/frontend/build

# Copy configuration files
COPY start.sh /app/start.sh
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Set correct permissions and ensure Unix line endings
RUN chmod +x /app/start.sh && \
    sed -i 's/\r$//' /app/start.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend
ENV PORT=3000
ENV API_PORT=8000
ENV DEBUG=False
ENV NODE_ENV=production

# Expose the ports
EXPOSE ${PORT}
EXPOSE ${API_PORT}

# Add healthcheck with improved configuration
HEALTHCHECK --interval=30s --timeout=60s --start-period=120s --retries=3 \
    CMD curl -f -H "X-Startup-Check: true" "http://localhost:${PORT}/api/health" || exit 1

# Start the application using the start.sh script
WORKDIR /app
CMD ["./start.sh"] 