import os
import sys

from django.apps import AppConfig


class FiscalisationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fiscalisation'

    def ready(self):
        # Skip the scheduler during management commands (migrate, shell, test,
        # collectstatic, etc.) — those shouldn't be dragging a background
        # thread along. Production WSGI (waitress / run.py) and `runserver`
        # both end up here without a skip-list match.
        argv = sys.argv
        skip = any(cmd in argv for cmd in (
            'migrate', 'makemigrations', 'shell', 'test', 'collectstatic',
            'createsuperuser', 'showmigrations', 'sqlmigrate', 'check',
            'dumpdata', 'loaddata', 'sync_pending_receipts',
        ))
        if skip:
            return
        # Django's autoreloader forks a child on `runserver`; only start the
        # scheduler in the child (where RUN_MAIN=true), not the parent.
        if 'runserver' in argv and os.environ.get('RUN_MAIN') != 'true':
            return

        try:
            from .scheduler import start_scheduler
            start_scheduler()
        except Exception as e:
            # Don't take the whole app down if APScheduler bootstrap fails.
            import logging
            logging.getLogger(__name__).warning("Scheduler did not start: %s", e)
