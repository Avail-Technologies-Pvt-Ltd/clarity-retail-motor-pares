import os
from pathlib import Path
from django.core.wsgi import get_wsgi_application
from point_of_sale.env import get_settings_module


os.environ.setdefault("DJANGO_SETTINGS_MODULE", get_settings_module())

application = get_wsgi_application()