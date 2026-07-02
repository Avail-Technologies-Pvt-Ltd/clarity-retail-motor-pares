"""
Production settings - PostgreSQL for client laptops
"""

import os
from .settings import *

# Load .env file (created by deploy.bat)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

# SECRET_KEY - get from environment with fallback for testing
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-12345-test-key-do-not-use-in-production")

# Initialize Sentry only if DSN is set
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_RATE", 0.1)),
        profiles_sample_rate=float(os.environ.get("SENTRY_TRACES_RATE", 0.05)),
        send_default_pii=True,
    )

# Use PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "point_of_sale"),
        "USER": os.environ.get("DB_USER", "pos_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
    }
}

# Production settings
DEBUG = True
ALLOWED_HOSTS = ["*"]

print("=" * 50)
print("PRODUCTION MODE - Using PostgreSQL Database")
print("=" * 50)
