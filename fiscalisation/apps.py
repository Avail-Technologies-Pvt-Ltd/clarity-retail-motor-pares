from django.apps import AppConfig

class FiscalisationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fiscalisation'

    def ready(self):
        # Start scheduler when Django starts
        from .scheduler import start_scheduler
        if not getattr(self, 'scheduler_started', False):
            start_scheduler()
            self.scheduler_started = True