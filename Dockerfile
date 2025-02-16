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
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Update pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY backend/requirements.txt backend/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application code
COPY backend/ backend/
COPY start.sh .
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create directory for frontend build
RUN mkdir -p /app/frontend/build

# Copy frontend build from build stage
COPY --from=frontend-build /app/frontend/build /app/frontend/build

# Set correct permissions
RUN chmod -R 755 /app && chmod +x /app/start.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend
ENV PORT=8000
ENV DEBUG=False
ENV NODE_ENV=production

# Expose the port
EXPOSE ${PORT}

# Start the application using the start.sh script
CMD ["./start.sh"] 