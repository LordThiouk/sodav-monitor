#!/bin/bash

echo "=== SODAV Monitor Backend Initialization ==="
echo "Starting initialization process..."
echo "Current directory: $(pwd)"

# Make run_app.py executable
chmod +x backend/run_app.py

# Clean the database
echo "Cleaning database..."
cd backend && python scripts/clean_db.py
if [ $? -eq 0 ]; then
    echo "✅ Database cleaned successfully"
else
    echo "❌ Error cleaning database"
    exit 1
fi

# Launch the backend
echo "Launching backend server..."
if [ -f "run_app.py" ]; then
    ./run_app.py
elif [ -f "../backend/run_app.py" ]; then
    cd .. && ./backend/run_app.py
else
    echo "❌ Error: run_app.py not found"
    exit 1
fi 