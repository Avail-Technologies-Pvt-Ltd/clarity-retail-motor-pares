"""
Production settings - PostgreSQL for client laptops
"""

import os
from .settings import *

# Load .env file (created by deploy.bat)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except ImportError:
    pass

# Use PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'point_of_sale'),
        'USER': os.environ.get('DB_USER', 'pos_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,
    }
}

# Production settings
DEBUG = False
ALLOWED_HOSTS = ['*']

print("=" * 50)
print("PRODUCTION MODE - Using PostgreSQL Database")
print("=" * 50)