#!/bin/bash
# entrypoint.sh

set -e

echo "========================================"
echo "Clarity POS - Starting Application"
echo "========================================"

# Wait for database
echo "Waiting for database..."
while ! nc -z $DB_HOST 5432; do
  sleep 0.1
done
echo "✅ Database is ready!"

# Run migrations
echo ""
echo "----------------------------------------"
echo "Running database migrations..."
echo "----------------------------------------"

python manage.py makemigrations --noinput || true
python manage.py migrate --noinput

echo "✅ Migrations completed!"

# Collect static files
echo ""
echo "----------------------------------------"
echo "Collecting static files..."
echo "----------------------------------------"
python manage.py collectstatic --noinput --no-post-process

echo "✅ Static files collected!"

echo ""
echo "========================================"
echo "Application is ready!"
echo "========================================"

# Execute the command passed to the container
exec "$@"