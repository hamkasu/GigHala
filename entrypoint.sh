#!/bin/bash
set -e

echo "========================================="
echo "GigHala Application Startup"
echo "========================================="

# Run database migrations
echo ""
echo "Running database migrations..."
echo "-----------------------------------------"

# Run invoice/receipt workflow migration
if [ -f "migrations/run_migration.py" ]; then
    echo "Running invoice/receipt workflow migration..."
    python migrations/run_migration.py || echo "Warning: Invoice/receipt migration had warnings"
fi

# Run approved budget migration
if [ -f "migrations/run_approved_budget_migration.py" ]; then
    echo "Running approved budget migration..."
    python migrations/run_approved_budget_migration.py || echo "Warning: Approved budget migration had warnings"
fi

echo ""
echo "========================================="
echo "Starting Gunicorn server..."
echo "========================================="
echo ""

# Start Gunicorn with the provided arguments
exec gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 180 --access-logfile - --error-logfile -
