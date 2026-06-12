# fiscalisation/apps.py
from django.apps import AppConfig
import os


class FiscalisationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fiscalisation'
    verbose_name = 'Fiscalisation Management'

    def ready(self):
        if os.environ.get('RUN_MAIN') or not os.environ.get('DJANGO_AUTORELOAD'):
            try:
                from fiscalisation.scheduler import start_background_sync
                from fiscalisation.models import FiscalisationSettings
                settings = FiscalisationSettings.get_settings()
                start_background_sync(interval_seconds=settings.sync_interval_seconds)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Background sync could not start: {e}")