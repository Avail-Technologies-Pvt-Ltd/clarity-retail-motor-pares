from dotenv import load_dotenv
from .settings import *
import os

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
        "Missing required variables in .env.dev.docker:\n"
        + "\n".join(f" - {name}" for name in missing)
    )

# ------------------------------------------------------------------------------
# Django Debug Toolbar
# ------------------------------------------------------------------------------

INSTALLED_APPS += [
    "debug_toolbar",
]

MIDDLEWARE.insert(
    1,
    "debug_toolbar.middleware.DebugToolbarMiddleware",
)

INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

# ------------------------------------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
]

# Use PostgreSQL for Docker development
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 600,
    }
}

ZIMRA_DEVICE_ID = os.getenv("ZIMRA_DEVICE_ID")
ZIMRA_SERIAL_NO = os.getenv("ZIMRA_SERIAL_NO")
ZIMRA_ACTIVATION_KEY = os.getenv("ZIMRA_ACTIVATION_KEY")
ZIMRA_TEST_MODE = os.getenv("ZIMRA_TEST_MODE", "True").lower() == "true"
ZIMRA_MODEL_NAME = os.getenv("ZIMRA_MODEL_NAME", "Server")
ZIMRA_MODEL_VERSION = os.getenv("ZIMRA_MODEL_VERSION", "v1")
ZIMRA_COMPANY_NAME = os.getenv("ZIMRA_COMPANY_NAME", "ClarityPOS")

print("=" * 60)
print("DEVELOPMENT MODE - Docker (PostgreSQL)")
print(f"Database : PostgreSQL ({DATABASES['default']['HOST']})")
print(f"Debug    : {DEBUG}")
print("=" * 60)