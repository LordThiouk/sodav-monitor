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

# Install system dependencies in a single layer with better error handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    gcc \
    python3-dev \
    libopenal1 \
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
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    gfortran \
    pkg-config \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/nginx \
    && mkdir -p /var/log/nginx \
    && mkdir -p /var/lib/nginx \
    && chown -R www-data:www-data /run/nginx \
    && chown -R www-data:www-data /var/log/nginx \
    && chown -R www-data:www-data /var/lib/nginx

# Set working directory and Python environment
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV PATH="/usr/local/bin:/root/.local/bin:${PATH}"

# Create log directory
RUN mkdir -p /app/backend/logs && chmod 777 /app/backend/logs

# Update pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

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

# Copy NGINX configuration files
COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf

# Create required NGINX directories and set permissions
RUN mkdir -p /var/log/nginx /var/cache/nginx /var/run/nginx && \
    chown -R nginx:nginx /var/log/nginx /var/cache/nginx /var/run/nginx && \
    chmod -R 755 /var/log/nginx /var/cache/nginx /var/run/nginx

# Set environment variables
ENV PORT=3000
ENV API_PORT=8000
ENV DEBUG=False
ENV NODE_ENV=production

# Expose ports
EXPOSE ${PORT}
EXPOSE ${API_PORT}

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=60s --start-period=120s --retries=3 \
    CMD curl -f -H "X-Startup-Check: true" "http://localhost:${PORT}/api/health" || exit 1

# Start the application
WORKDIR /app
CMD ["./start.sh"] 