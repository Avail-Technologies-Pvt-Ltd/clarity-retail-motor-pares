"""
Development settings - SQLite for local development
"""

from .settings import *

# Use SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Development settings
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

print("=" * 50)
print("DEVELOPMENT MODE - Using SQLite Database")
print("=" * 50)