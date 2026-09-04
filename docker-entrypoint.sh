#!/bin/sh

set -e

echo "========================================"
echo " Clarity Retail - Container Startup"
echo "========================================"

echo ""
echo "Waiting for PostgreSQL..."

until python -c "
import os
import socket

host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', '5432'))

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2)

try:
    sock.connect((host, port))
    sock.close()
    exit(0)
except Exception:
    exit(1)
"; do
    echo "PostgreSQL is not ready yet..."
    sleep 2
done

echo "PostgreSQL is ready."
echo ""

echo "Running database migrations..."
python manage.py migrate --noinput

echo ""
echo "Database migrations completed."
echo ""

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "Static files collected."
echo ""

if [ "$DJANGO_ENV" = "development" ]; then

    echo "Starting Django development server..."
    exec python manage.py runserver 0.0.0.0:8000

else

    echo "Starting Gunicorn..."
    exec gunicorn point_of_sale.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 3 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -

fi