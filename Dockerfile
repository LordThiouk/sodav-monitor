# Use a specific Python version
FROM python:3.9.18-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    libopenal1 \
    python3-dev \
    ffmpeg \
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

# Set correct permissions
RUN chmod -R 755 /app && chmod +x /app/start.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend
ENV PORT=8000
ENV DEBUG=True

# Expose the port
EXPOSE ${PORT}

# Start the application
CMD ["/app/start.sh"] 