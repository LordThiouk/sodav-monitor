#!/bin/bash
# Force new deployment - $(date)
set -e

# Ensure correct PATH
export PATH="/usr/local/bin:/root/.local/bin:${PATH}"

# Function to verify package installation
verify_package() {
    local pkg=$1
    local version_cmd=$2
    echo "Verifying $pkg installation..."
    if ! python3 -c "import $pkg" &> /dev/null; then
        echo "❌ $pkg not found!"
        return 1
    fi
    if [ -n "$version_cmd" ]; then
        echo "✅ $pkg version: $(python3 -c "$version_cmd" 2>/dev/null || echo 'version check failed')"
    else
        echo "✅ $pkg is installed"
    fi
    return 0
}

# Check core dependencies with better error handling
echo "Checking core dependencies..."
PACKAGES=(
    "uvicorn:print(__import__('uvicorn').__version__)"
    "fastapi:print(__import__('fastapi').__version__)"
    "alembic:print(__import__('alembic').__version__)"
    "sqlalchemy:print(__import__('sqlalchemy').__version__)"
    "jose:print(__import__('jose').__version__)"
    "passlib:print(__import__('passlib').__version__)"
    "pydub:print(__import__('pydub').__version__)"
    "musicbrainzngs:print(__import__('musicbrainzngs').__version__)"
    "numpy:print(__import__('numpy').__version__)"
    "scipy:print(__import__('scipy').__version__)"
    "librosa:print(__import__('librosa').__version__)"
    "pandas:print(__import__('pandas').__version__)"
    "numba:print(__import__('numba').__version__)"
)

INSTALL_NEEDED=false
for pkg_info in "${PACKAGES[@]}"; do
    pkg="${pkg_info%%:*}"
    version_cmd="${pkg_info#*:}"
    if ! verify_package "$pkg" "$version_cmd"; then
        INSTALL_NEEDED=true
        break
    fi
done

if [ "$INSTALL_NEEDED" = true ]; then
    echo "Installing missing dependencies..."
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
        llvmlite==0.39.1
    
    # Verify installations again
    echo "Verifying installations after install..."
    for pkg_info in "${PACKAGES[@]}"; do
        pkg="${pkg_info%%:*}"
        version_cmd="${pkg_info#*:}"
        if ! verify_package "$pkg" "$version_cmd"; then
            echo "❌ Failed to install $pkg"
            pip show $pkg || true
            exit 1
        fi
    done
fi

# Verify uvicorn installation
if ! command -v uvicorn &> /dev/null; then
    echo "❌ uvicorn command not found. Installing..."
    pip install --no-cache-dir uvicorn==0.22.0
    
    if ! command -v uvicorn &> /dev/null; then
        echo "❌ Failed to install uvicorn. Checking installation details..."
        pip show uvicorn
        echo "Current PATH: $PATH"
        echo "Python executable: $(which python3)"
        echo "Pip executable: $(which pip)"
        echo "uvicorn location: $(find / -name uvicorn 2>/dev/null)"
        exit 1
    fi
fi

echo "✅ uvicorn is installed and available"

# Check if Alembic is installed and available
if ! command -v alembic &> /dev/null
then
    echo "❌ Alembic not found! Installing..."
    pip install --no-cache-dir --upgrade pip setuptools wheel
    pip install --no-cache-dir \
        alembic==1.13.1 \
        psycopg2-binary>=2.9.9 \
        SQLAlchemy>=2.0.15 \
        python-dotenv>=1.0.0
    
    # Verify installation
    if ! command -v alembic &> /dev/null
    then
        echo "❌ Failed to install Alembic. Checking installation details..."
        pip show alembic
        echo "Current PATH: $PATH"
        echo "Alembic location: $(find / -name alembic 2>/dev/null)"
        exit 1
    fi
    echo "✅ Alembic installed successfully!"
fi

# Verify Alembic version
ALEMBIC_VERSION=$(alembic --version)
echo "Using Alembic version: $ALEMBIC_VERSION"

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
    echo "Converting postgres:// to postgresql:// in DATABASE_URL"
    export DATABASE_URL=$(echo $DATABASE_URL | sed 's/postgres:\/\//postgresql:\/\//')
    if [[ $? -ne 0 ]]; then
        echo "❌ Error: Failed to convert DATABASE_URL format"
        exit 1
    fi
    echo "✅ Successfully converted DATABASE_URL format"
fi

# Validate DATABASE_URL format
if [[ ! $DATABASE_URL =~ ^postgresql://[^:]+:[^@]+@[^:]+:[0-9]+/[^/]+$ ]]; then
    echo "❌ Error: Invalid DATABASE_URL format"
    echo "Expected format: postgresql://user:password@host:port/dbname"
    exit 1
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

# Wait for PostgreSQL with increased timeout and better logging
for i in {1..60}; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    
    if [ $i -eq 60 ]; then
        echo "❌ Error: PostgreSQL did not become ready in time"
        exit 1
    fi
    
    echo "⏳ Waiting for PostgreSQL... attempt $i/60"
    sleep 2
done

# Apply database migrations with better error handling
echo "Applying database migrations..."
cd /app/backend
echo "Current directory: $(pwd)"
echo "Checking for alembic.ini..."

if [ ! -f "alembic.ini" ]; then
    echo "❌ Error: alembic.ini not found"
    ls -la
    exit 1
fi

echo "Found alembic.ini"
cat alembic.ini | grep -A 5 "\[alembic\]"

echo "Checking migrations directory..."
if [ ! -d "migrations" ]; then
    echo "❌ Error: migrations directory not found"
    exit 1
fi

echo "Checking migrations/env.py..."
if [ ! -f "migrations/env.py" ]; then
    echo "❌ Error: migrations/env.py not found"
    ls -la migrations/
    exit 1
fi

echo "Running database migrations..."
if ! PYTHONPATH=/app/backend alembic upgrade head; then
    echo "❌ Error: Database migration failed"
    exit 1
fi
echo "✅ Database migrations applied successfully"

# Set Python path
export PYTHONPATH=/app/backend:$PYTHONPATH

# Kill any existing processes more gracefully
echo "Checking for existing processes..."
if pgrep -f "uvicorn main:app" > /dev/null; then
    echo "🔄 Stopping existing Uvicorn process..."
    pkill -f "uvicorn main:app" || true
    sleep 2
fi

if pgrep nginx > /dev/null; then
    echo "🔄 Stopping existing Nginx process..."
    pkill nginx || true
    sleep 2
fi

# Start the FastAPI application with better logging and error handling
cd /app/backend
echo "Starting FastAPI application..."
python3 -m uvicorn main:app --host 0.0.0.0 --port $API_PORT --workers 1 --log-level debug --timeout-keep-alive 120 &
FASTAPI_PID=$!

# Wait for FastAPI to start with improved health check
echo "Waiting for FastAPI to start..."
HEALTH_CHECK_TIMEOUT=120
HEALTH_CHECK_INTERVAL=2
ATTEMPTS=$((HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL))

for i in $(seq 1 $ATTEMPTS); do
    if ! ps -p $FASTAPI_PID > /dev/null; then
        echo "❌ Error: FastAPI process died unexpectedly"
        exit 1
    fi
    
    HEALTH_RESPONSE=$(curl -s -H "X-Startup-Check: true" "http://127.0.0.1:$API_PORT/api/health" || true)
    if [[ "$HEALTH_RESPONSE" == *"healthy"* ]] || [[ "$HEALTH_RESPONSE" == *"ok"* ]] || [[ "$HEALTH_RESPONSE" == *"starting"* ]]; then
        echo "✅ FastAPI is running on port $API_PORT!"
        break
    fi
    
    if [ $i -eq $ATTEMPTS ]; then
        echo "❌ Error: FastAPI did not start properly after $HEALTH_CHECK_TIMEOUT seconds"
        echo "Health check response: $HEALTH_RESPONSE"
        echo "FastAPI logs:"
        tail -n 50 /app/backend/logs/fastapi.log || true
        if [ -n "$FASTAPI_PID" ]; then
            kill $FASTAPI_PID || true
        fi
        exit 1
    fi
    
    echo "⏳ Waiting for FastAPI... attempt $i/$ATTEMPTS"
    sleep $HEALTH_CHECK_INTERVAL
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

# Configure nginx with better error handling
echo "Configuring nginx..."
export NGINX_PORT=$PORT
# Use envsubst to replace the port in the nginx configuration
envsubst '$PORT' < /etc/nginx/conf.d/default.conf > /etc/nginx/conf.d/default.conf.tmp
mv /etc/nginx/conf.d/default.conf.tmp /etc/nginx/conf.d/default.conf

# Test nginx configuration
echo "Testing nginx configuration..."
if ! nginx -t; then
    echo "❌ Error: Invalid nginx configuration"
    exit 1
fi

# Start nginx
echo "Starting nginx..."
nginx -g "daemon off;" &
NGINX_PID=$!

# Wait for nginx to start
echo "Waiting for nginx to start..."
for i in {1..60}; do
    if curl -s -H "X-Startup-Check: true" "http://127.0.0.1:$PORT/api/health" > /dev/null; then
        echo "✅ Nginx is running on port $PORT!"
        break
    fi
    
    if [ $i -eq 60 ]; then
        echo "❌ Error: Nginx did not start properly"
        if [ -n "$NGINX_PID" ]; then
            kill $NGINX_PID || true
        fi
        exit 1
    fi
    
    echo "⏳ Waiting for Nginx... attempt $i/60"
    sleep 2
done

# Final health check through Nginx
FINAL_HEALTH_CHECK=$(curl -s -H "X-Startup-Check: true" "http://127.0.0.1:$PORT/api/health")
if [[ "$FINAL_HEALTH_CHECK" != *"healthy"* ]] && [[ "$FINAL_HEALTH_CHECK" != *"starting"* ]]; then
    echo "❌ Final health check failed: $FINAL_HEALTH_CHECK"
    exit 1
fi

echo "✅ Application started successfully!"
echo "FastAPI running on port $API_PORT"
echo "Nginx running on port $PORT"

# Disable startup grace period after successful startup
export STARTUP_GRACE_PERIOD=false
echo "Startup grace period disabled"

# Monitor both processes
while true; do
    if ! ps -p $FASTAPI_PID > /dev/null || ! ps -p $NGINX_PID > /dev/null; then
        echo "❌ One of the processes died"
        exit 1
    fi
    sleep 10
done