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

# Install essential Python packages first
RUN pip install --no-cache-dir \
    python-dotenv>=1.0.0 \
    alembic>=1.13.1 \
    psycopg2-binary>=2.9.9 \
    SQLAlchemy>=2.0.15

# Copy requirements first for better caching
COPY backend/requirements.txt ./

# Install remaining Python dependencies with retry mechanism
RUN for i in {1..3}; do \
    pip install --no-cache-dir -r requirements.txt && break || sleep 2; \
    done

# Ensure Alembic is in PATH
RUN ln -s /usr/local/bin/alembic /usr/bin/alembic

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