# Updated Dockerfile to trigger rebuild - v2
# Build stage for frontend
FROM node:18-alpine as frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Build stage for backend
FROM python:3.9.18-slim-bullseye

# Install system dependencies and configure nginx in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    gcc \
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
    libportaudio2 \
    python3-scipy \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/nginx /var/log/nginx /var/lib/nginx /var/cache/nginx /var/run/nginx \
    && groupadd -r nginx \
    && useradd -r -g nginx nginx \
    && chown -R nginx:nginx /run/nginx /var/log/nginx /var/lib/nginx /var/cache/nginx /var/run/nginx \
    && chmod -R 755 /run/nginx /var/log/nginx /var/lib/nginx /var/cache/nginx /var/run/nginx

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

# Create log directory
RUN mkdir -p /app/backend/logs && chmod 777 /app/backend/logs

# Install Python dependencies in a single layer
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Install core dependencies in a single layer with explicit versions and better error handling
RUN echo "Installing core dependencies..." && \
    pip install --no-cache-dir \
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
    psutil>=5.9.0 \
    && echo "Core dependencies installed successfully" \
    && python3 -m pip show uvicorn \
    && python3 -c "import uvicorn; print(f'uvicorn version: {uvicorn.__version__}')" \
    && python3 -c "import fastapi; print(f'fastapi version: {fastapi.__version__}')" \
    && python3 -c "import alembic; print(f'alembic version: {alembic.__version__}')" \
    && python3 -c "import jose; print(f'python-jose version: {jose.__version__}')" \
    && python3 -c "import passlib; print(f'passlib version: {passlib.__version__}')" \
    && python3 -m pip show musicbrainzngs | grep "Version:" \
    && python3 -c "import numpy; print(f'numpy version: {numpy.__version__}')" \
    && python3 -c "import scipy; print(f'scipy version: {scipy.__version__}')" \
    && python3 -c "import librosa; print(f'librosa version: {librosa.__version__}')"

# Copy backend files
COPY backend/ ./
COPY backend/migrations ./migrations/
RUN chmod -R 755 migrations

# Copy frontend build and configuration files
COPY --from=frontend-build /app/frontend/build /app/frontend/build
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh && \
    sed -i 's/\r$//' /app/start.sh  # Fix line endings for Windows
COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf

# Expose ports
EXPOSE ${PORT} ${API_PORT}

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=60s --start-period=120s --retries=3 \
    CMD curl -f -H "X-Startup-Check: true" "http://localhost:${PORT}/api/health" || exit 1

# Start the application
WORKDIR /app
CMD ["./start.sh"] 