"""
Django base settings for point_of_sale project.
Database is configured in environment-specific files.
"""

import os
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep secret key in environment variable
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key')


# Debug - will be overridden in dev/prod
DEBUG = True

# Allowed hosts
ALLOWED_HOSTS = ['*']

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Application definition
INSTALLED_APPS = [
    'accounts',
    'enventory',
    'payments',
    'pos',
    'fiscalisation',
    'order',
    'knowledge_base',
    'django_filters',
    'mathfilters',
    'django.contrib.humanize',
    'rest_framework',
    'rest_framework.authtoken',
    'whitenoise.runserver_nostatic',
    'django_apscheduler',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "point_of_sale.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "point_of_sale.wsgi.application"

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / 'tmp/django_cache',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get('TIME_ZONE', 'Africa/Harare')
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'login_page'
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Security for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True



# ZIMRA Configuration - Direct values
ZIMRA_DEVICE_ID = '10626'
ZIMRA_SERIAL_NO = '9029D38C011B'
ZIMRA_ACTIVATION_KEY = '00398834'
ZIMRA_TEST_MODE = True

# Certificate paths
ZIMRA_CERT_PATH = os.path.join(BASE_DIR, 'certs', 'certificate.crt')
ZIMRA_KEY_PATH = os.path.join(BASE_DIR, 'certs', 'decrypted_key.key')
ZIMRA_FOLDER_NAME = os.path.join(BASE_DIR, 'certs')


# ZIMRA Configuration
ZIMRA_DEVICE_ID = os.environ.get('ZIMRA_DEVICE_ID', '10626')
ZIMRA_SERIAL_NO = os.environ.get('ZIMRA_SERIAL_NO', '9029D38C011B')
ZIMRA_ACTIVATION_KEY = os.environ.get('ZIMRA_ACTIVATION_KEY', '00398834')
ZIMRA_TEST_MODE = os.environ.get('ZIMRA_TEST_MODE', 'True').lower() == 'true'
ZIMRA_MODEL_NAME = os.environ.get('ZIMRA_MODEL_NAME', 'Server')
ZIMRA_MODEL_VERSION = os.environ.get('ZIMRA_MODEL_VERSION', 'v1')
ZIMRA_COMPANY_NAME = os.environ.get('ZIMRA_COMPANY_NAME', 'ClarityPOS')

# Certificate paths
CERTS_DIR = os.path.join(BASE_DIR, 'certs')
ZIMRA_FOLDER_NAME = CERTS_DIR
ZIMRA_CERT_PATH = os.path.join(CERTS_DIR, 'certificate.crt')
ZIMRA_KEY_PATH = os.path.join(CERTS_DIR, 'decrypted_key.key')

# Create certs directory if it doesn't exist
os.makedirs(CERTS_DIR, exist_ok=True)