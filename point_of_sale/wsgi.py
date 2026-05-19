"""
WSGI config for point_of_sale project.
Uses production settings for WSGI server (Waitress).
"""

import os

# For WSGI (Waitress), use production settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'point_of_sale.settings_prod')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()