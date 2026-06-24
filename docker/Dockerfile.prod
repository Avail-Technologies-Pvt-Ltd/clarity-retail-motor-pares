FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .
RUN pip install --no-cache-dir --timeout=100 --retries=5 -r requirements-docker.txt

COPY . .

RUN mkdir -p /app/logs /app/media /app/staticfiles /app/tmp

ENV DJANGO_SETTINGS_MODULE=point_of_sale.settings_prod
ENV PYTHONUNBUFFERED=1
ENV DEBUG=False

RUN python manage.py collectstatic --noinput || true

# Container listens on port 8000 internally
# docker-compose maps it to 8001 externally
EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn --bind 0.0.0.0:8000 point_of_sale.wsgi:application"]