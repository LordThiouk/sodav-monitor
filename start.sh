#!/bin/bash
set -e

# Ensure PORT is set
export PORT=${PORT:-3000}
export API_PORT=8000  # Port pour FastAPI
echo "Starting application (API on $API_PORT, nginx on $PORT)"

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

# Wait for PostgreSQL
for i in {1..30}; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; then
        echo "PostgreSQL is ready!"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo "Error: PostgreSQL did not become ready in time"
        exit 1
    fi
    
    echo "Waiting for PostgreSQL... attempt $i/30"
    sleep 1
done

# Verify frontend build exists
if [ ! -d "/app/frontend/build" ]; then
    echo "ERROR: Frontend build directory not found!"
    exit 1
fi

# Verify static directory exists
if [ ! -d "/app/frontend/build/static" ]; then
    echo "ERROR: Frontend static directory not found!"
    exit 1
fi

cd backend

# Apply database migrations
echo "Applying database migrations..."
alembic upgrade head

# Stop nginx if it's running
echo "Stopping nginx if running..."
if [ -f "/app/nginx.pid" ]; then
    nginx -s quit || true
    rm -f /app/nginx.pid
fi
sleep 2

# Configure nginx
echo "Configuring nginx..."
export NGINX_PORT=$PORT
sed -i "s/listen [0-9]* default_server/listen $NGINX_PORT default_server/g" /etc/nginx/conf.d/default.conf
sed -i "s/127.0.0.1:8001/127.0.0.1:$API_PORT/g" /etc/nginx/conf.d/default.conf

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t || exit 1

# Start nginx
echo "Starting nginx..."
nginx

# Function to check if a port is open
check_port() {
    local port=$1
    if command -v nc >/dev/null 2>&1; then
        nc -z 127.0.0.1 "$port" >/dev/null 2>&1
        return $?
    elif command -v curl >/dev/null 2>&1; then
        curl -s -o /dev/null "http://127.0.0.1:$port/health"
        return $?
    elif command -v wget >/dev/null 2>&1; then
        wget -q --spider "http://127.0.0.1:$port/health"
        return $?
    else
        # If no tools are available, try a basic TCP connection using bash
        (echo > "/dev/tcp/127.0.0.1/$port") >/dev/null 2>&1
        return $?
    fi
}

# Wait for nginx to start
echo "Waiting for nginx to start..."
max_attempts=10
attempt=1
while [ $attempt -le $max_attempts ]; do
    if check_port "$NGINX_PORT"; then
        echo "✅ Nginx is running on port $NGINX_PORT!"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ Error: Nginx did not start properly"
        echo "📋 Nginx error log:"
        if [ -f "/var/log/nginx/error.log" ]; then
            cat /var/log/nginx/error.log
        else
            echo "No error log found at /var/log/nginx/error.log"
        fi
        nginx -t
        exit 1
    fi
    
    echo "⏳ Waiting for nginx... attempt $attempt/$max_attempts"
    sleep 2
    attempt=$((attempt + 1))
done

# Start FastAPI application
echo "Starting FastAPI application..."
if [ "$DEBUG" = "true" ]; then
    uvicorn main:app --host 127.0.0.1 --port $API_PORT --reload
else
    uvicorn main:app --host 127.0.0.1 --port $API_PORT
fi 