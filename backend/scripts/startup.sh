#!/bin/bash
# Startup script for Common Investor API
# Handles migrations and optional auto-seeding on first startup

set -e

echo "=== Common Investor API Startup ==="

# Wait for database to be ready
echo "Waiting for database..."
sleep 10

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Check if auto-seeding is enabled and DB is empty
if [ "${AUTO_SEED:-true}" = "true" ]; then
    echo "Checking if database needs seeding..."
    
    # Run seed check - exit code 1 means seeding is needed
    if python -m app.cli.seed --check; then
        echo "Database already has data. Skipping auto-seed."
    else
        echo "Database is empty. Running auto-seed..."
        python -m app.cli.seed --delay 1.0
    fi
else
    echo "Auto-seeding disabled (AUTO_SEED=false)"
fi

# Start the API server
echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
