from dotenv import load_dotenv
from .settings import *

load_dotenv(BASE_DIR / ".env")


OLD_PRINT = os.getenv("OLD_PRINT")
print(f'OLD PRINT MODE {OLD_PRINT}')



# ------------------------------------------------------------------------------
# Validate Required Environment Variables
# ------------------------------------------------------------------------------

required = [
    "SECRET_KEY",
    "OLD_PRINT",
]

missing = [name for name in required if not os.getenv(name)]

if missing:
    raise RuntimeError(
        "Missing required variables in .env:\n"
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
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
print("DEVELOPMENT MODE - Env (sqlite3)")
print(f"Database : sqlite3")
print(f"Debug    : {DEBUG}")
print("=" * 60)