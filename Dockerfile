# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    netcat-traditional \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements-docker.txt .

# Install Python dependencies
# RUN pip install --no-cache-dir \
RUN pip install  \
    --timeout=100 \
    --retries=5 \
    -r requirements-docker.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p \
    /app/logs \
    /app/media \
    /app/staticfiles \
    /app/tmp

# Set environment variables
ENV DJANGO_SETTINGS_MODULE=point_of_sale.settings_prod
ENV PYTHONUNBUFFERED=1
ENV DEBUG=False

# Copy and setup entrypoint - ALL DONE INSIDE DOCKER
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# Don't run collectstatic here - it will run at container startup

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "point_of_sale.wsgi:application"]