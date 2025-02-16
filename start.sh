#!/bin/bash
set -e

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

cd backend

# Apply database migrations
echo "Applying database migrations..."
alembic upgrade head

echo "Starting the application..."
if [ "$DEBUG" = "True" ]; then
    echo "Running in DEBUG mode"
    exec uvicorn main:app --host 0.0.0.0 --port $PORT --reload --log-level debug
else
    exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4 
fi 