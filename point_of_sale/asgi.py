"""
ASGI config for point_of_sale project.
"""

import os
from pathlib import Path
from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "point_of_sale.settings_dev")

application = get_asgi_application()