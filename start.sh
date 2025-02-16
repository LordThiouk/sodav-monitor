#!/bin/bash
set -e

# Ensure PORT is set
export PORT=${PORT:-8000}
echo "Starting application on port $PORT"

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
nginx -s quit || true
sleep 2

# Configure nginx
echo "Configuring nginx..."
export NGINX_PORT=$PORT
export API_PORT=8000
sed -i "s/\$PORT/$NGINX_PORT/g" /etc/nginx/conf.d/default.conf

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t || exit 1

# Start nginx
echo "Starting nginx..."
nginx

# Wait for nginx to start
echo "Waiting for nginx to start..."
for i in {1..10}; do
    if command -v curl >/dev/null 2>&1; then
        if curl -s http://127.0.0.1:$NGINX_PORT/health > /dev/null; then
            echo "Nginx is running!"
            break
        fi
    else
        if nc -z 127.0.0.1 $NGINX_PORT; then
            echo "Nginx is running! (checked with netcat)"
            break
        fi
    fi
    
    if [ $i -eq 10 ]; then
        echo "Error: Nginx did not start properly"
        echo "Nginx error log:"
        cat /var/log/nginx/error.log
        exit 1
    fi
    
    echo "Waiting for nginx... attempt $i/10"
    sleep 2
done

# Start FastAPI application
echo "Starting FastAPI application..."
if [ "$DEBUG" = "true" ]; then
    uvicorn main:app --host 127.0.0.1 --port $API_PORT --reload
else
    uvicorn main:app --host 127.0.0.1 --port $API_PORT
fi 