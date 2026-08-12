"""
ASGI config for point_of_sale project.
"""

import os
from pathlib import Path
from django.core.asgi import get_asgi_application
from point_of_sale.env import get_settings_module


os.environ.setdefault("DJANGO_SETTINGS_MODULE", get_settings_module())

application = get_asgi_application()