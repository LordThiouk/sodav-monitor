#!/bin/bash
set -e

# Ensure PORT is set
export PORT=${PORT:-3000}
export API_PORT=8000
echo "Starting application (API on $API_PORT, nginx on $PORT)"

# Set startup grace period
export STARTUP_GRACE_PERIOD=true
echo "Startup grace period enabled"

# Use DATABASE_PUBLIC_URL if DATABASE_URL is not set
if [[ -z "${DATABASE_URL}" ]]; then
    if [[ -z "${DATABASE_PUBLIC_URL}" ]]; then
        echo "ERROR: Neither DATABASE_URL nor DATABASE_PUBLIC_URL is set!"
        exit 1
    else
        echo "DATABASE_URL not set, using DATABASE_PUBLIC_URL instead"
        export DATABASE_URL="${DATABASE_PUBLIC_URL}"
    fi
fi

echo "Database URL found. Attempting connection..."

# Convert postgres:// to postgresql:// if needed
if [[ $DATABASE_URL == postgres://* ]]; then
    export DATABASE_URL=$(echo $DATABASE_URL | sed 's/postgres:\/\//postgresql:\/\//')
    echo "Converted postgres:// to postgresql:// in DATABASE_URL"
fi

# Extract database connection details from DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set"
    exit 1
fi

DB_HOST=$(echo $DATABASE_URL | sed -E 's/.*@([^:]+):.*/\1/')
DB_PORT=$(echo $DATABASE_URL | sed -E 's/.*:([0-9]+)\/.*/\1/')
DB_USER=$(echo $DATABASE_URL | sed -E 's/.*:\/\/([^:]+):.*/\1/')
DB_PASSWORD=$(echo $DATABASE_URL | sed -E 's/.*:([^@]+)@.*/\1/')

echo "Waiting for PostgreSQL to be ready..."
export PGPASSWORD=$DB_PASSWORD

# Wait for PostgreSQL with increased timeout
for i in {1..60}; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; then
        echo "PostgreSQL is ready!"
        break
    fi
    
    if [ $i -eq 60 ]; then
        echo "Error: PostgreSQL did not become ready in time"
        exit 1
    fi
    
    echo "Waiting for PostgreSQL... attempt $i/60"
    sleep 2
done

# Apply database migrations
echo "Applying database migrations..."
cd /app/backend
alembic upgrade head

# Set Python path
export PYTHONPATH=/app/backend:$PYTHONPATH

# Kill any existing processes
pkill -f "uvicorn main:app" || true
pkill nginx || true

# Start the FastAPI application
cd /app/backend
echo "Starting FastAPI application..."
python3 -m uvicorn main:app --host 0.0.0.0 --port $API_PORT --workers 1 &
FASTAPI_PID=$!

# Wait for FastAPI to start with increased timeout and better health check
echo "Waiting for FastAPI to start..."
for i in {1..60}; do
    HEALTH_RESPONSE=$(curl -s -H "X-Startup-Check: true" "http://127.0.0.1:$API_PORT/api/health")
    if [[ "$HEALTH_RESPONSE" == *"healthy"* ]] || [[ "$HEALTH_RESPONSE" == *"ok"* ]]; then
        echo "✅ FastAPI is running on port $API_PORT!"
        break
    fi
    
    if [ $i -eq 60 ]; then
        echo "❌ Error: FastAPI did not start properly"
        echo "Health check response: $HEALTH_RESPONSE"
        if [ -n "$FASTAPI_PID" ]; then
            kill $FASTAPI_PID || true
        fi
        exit 1
    fi
    
    echo "Waiting for FastAPI... attempt $i/60"
    sleep 2
done

# Ensure nginx directories exist with proper permissions
echo "Setting up nginx directories..."
mkdir -p /run/nginx /var/log/nginx /var/lib/nginx
chown -R www-data:www-data /run/nginx /var/log/nginx /var/lib/nginx
chmod -R 755 /run/nginx /var/log/nginx /var/lib/nginx

# Stop nginx if it's running
echo "Stopping nginx if running..."
if [ -f "/run/nginx/nginx.pid" ]; then
    nginx -s quit || true
    sleep 5
    if [ -f "/run/nginx/nginx.pid" ]; then
        rm -f /run/nginx/nginx.pid
    fi
fi

# Configure nginx
echo "Configuring nginx..."
export NGINX_PORT=$PORT
sed -i "s/listen [0-9]* default_server/listen $NGINX_PORT default_server/g" /etc/nginx/conf.d/default.conf

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t || exit 1

# Start nginx
echo "Starting nginx..."
nginx -g 'daemon off;' &
NGINX_PID=$!

# Wait for nginx to start with better health check
echo "Waiting for nginx to start..."
for i in {1..30}; do
    if curl -s -H "X-Startup-Check: true" "http://127.0.0.1:$PORT/api/health" > /dev/null; then
        echo "✅ Nginx is running on port $PORT!"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo "❌ Error: Nginx did not start properly"
        if [ -n "$NGINX_PID" ]; then
            kill $NGINX_PID || true
        fi
        if [ -n "$FASTAPI_PID" ]; then
            kill $FASTAPI_PID || true
        fi
        exit 1
    fi
    
    echo "Waiting for Nginx... attempt $i/30"
    sleep 1
done

# Disable startup grace period only after both services are running
export STARTUP_GRACE_PERIOD=false
echo "Startup grace period disabled"

# Monitor both processes
while true; do
    if ! kill -0 $FASTAPI_PID 2>/dev/null; then
        echo "❌ FastAPI process died"
        if [ -n "$NGINX_PID" ]; then
            kill $NGINX_PID || true
        fi
        exit 1
    fi
    
    if ! kill -0 $NGINX_PID 2>/dev/null; then
        echo "❌ Nginx process died"
        if [ -n "$FASTAPI_PID" ]; then
            kill $FASTAPI_PID || true
        fi
        exit 1
    fi
    
    sleep 5
done 