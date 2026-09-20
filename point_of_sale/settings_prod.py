"""
Production settings for point_of_sale.

This file is loaded automatically when .env exists.
"""

import os

from dotenv import load_dotenv

from .settings import *


# ------------------------------------------------------------------------------
# Validate Required Environment Variables
# ------------------------------------------------------------------------------

required = [
    "SECRET_KEY",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
]

missing = [name for name in required if not os.getenv(name)]

if missing:
    raise RuntimeError(
        "Missing required variables in .env:\n"
        + "\n".join(f" - {name}" for name in missing)
    )

# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Security
# ------------------------------------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "*").split(",")
    if host.strip()
]

# ------------------------------------------------------------------------------
# Database (PostgreSQL)
# ------------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
    }
}

# ------------------------------------------------------------------------------
# Security Headers
# ------------------------------------------------------------------------------

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Enable these only when using HTTPS
SESSION_COOKIE_SECURE = os.getenv(
    "SESSION_COOKIE_SECURE", "False"
).lower() == "true"

CSRF_COOKIE_SECURE = os.getenv(
    "CSRF_COOKIE_SECURE", "False"
).lower() == "true"

SECURE_SSL_REDIRECT = os.getenv(
    "SECURE_SSL_REDIRECT", "False"
).lower() == "true"

# ------------------------------------------------------------------------------
# Sentry
# ------------------------------------------------------------------------------

SENTRY_DSN = os.getenv("SENTRY_DSN")

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=float(
            os.getenv("SENTRY_TRACES_RATE", "0.1")
        ),
        profiles_sample_rate=float(
            os.getenv("SENTRY_PROFILES_RATE", "0.05")
        ),
        send_default_pii=True,
    )

# ------------------------------------------------------------------------------
# ZIMRA Configuration
# ------------------------------------------------------------------------------

ZIMRA_DEVICE_ID = os.getenv("ZIMRA_DEVICE_ID")
ZIMRA_SERIAL_NO = os.getenv("ZIMRA_SERIAL_NO")
ZIMRA_ACTIVATION_KEY = os.getenv("ZIMRA_ACTIVATION_KEY")

ZIMRA_TEST_MODE = os.getenv(
    "ZIMRA_TEST_MODE", "False"
).lower() == "true"

ZIMRA_MODEL_NAME = os.getenv(
    "ZIMRA_MODEL_NAME",
    "Server",
)

ZIMRA_MODEL_VERSION = os.getenv(
    "ZIMRA_MODEL_VERSION",
    "v1",
)

ZIMRA_COMPANY_NAME = os.getenv(
    "ZIMRA_COMPANY_NAME",
    "ClarityPOS",
)

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------

print("=" * 60)
print("RUNNING IN PRODUCTION MODE")
print(f"Database : PostgreSQL ({DATABASES['default']['HOST']})")
print(f"Debug    : {DEBUG}")
print("=" * 60)