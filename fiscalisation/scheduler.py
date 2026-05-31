"""In-process scheduler so the POS box doesn't need cron or a worker daemon.

What gets scheduled:
  * sync_pending_receipts — every 2 minutes. Pushes any PENDING FiscalReceipt
    rows (those signed locally during a checkout while ZIMRA was down/slow)
    up to ZIMRA. Stays put if there's nothing to do.
  * reconcile_with_zimra  — once a day at 04:00 CAT. Catches state drift from
    manual closes / network glitches without anyone needing to click anything.

How it's wired:
  * fiscalisation.apps.FiscalisationConfig.ready() calls start_scheduler().
  * django_apscheduler's DjangoJobStore persists job definitions to the DB so
    they survive process restarts. The schedule itself is hardcoded here —
    replace_existing=True means changes to the schedule below take effect on
    the next process start.
  * Single-process WSGI server (waitress in run.py): no cross-worker
    coordination needed. If you later move to gunicorn with workers > 1,
    only one worker should run this — gate it with an env flag or use
    APScheduler's redis lock.
"""

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# The scheduler fires triggers in Zimbabwe local time, independent of Django's
# TIME_ZONE. Otherwise a "04:00 daily" job would fire at 06:00 CAT on a
# UTC-configured Django process.
try:
    from zoneinfo import ZoneInfo
    SCHEDULER_TZ = ZoneInfo('Africa/Harare')
except Exception:
    from datetime import timezone, timedelta
    SCHEDULER_TZ = timezone(timedelta(hours=2), name='CAT')

_scheduler = None


def _run_sync_pending():
    """Job entry point — call the management command in-process."""
    from django.core.management import call_command
    try:
        call_command('sync_pending_receipts')
    except Exception:
        logger.exception("scheduled sync_pending_receipts failed")


def _run_daily_reconcile():
    from fiscalisation.views import reconcile_with_zimra
    try:
        result = reconcile_with_zimra()
        logger.info("daily reconcile: %s", result)
    except Exception:
        logger.exception("daily reconcile failed")


def _prune_history():
    """Drop APScheduler job-execution rows older than 30 days."""
    from django_apscheduler.models import DjangoJobExecution
    try:
        DjangoJobExecution.objects.delete_old_job_executions(86400 * 30)
    except Exception:
        logger.exception("APScheduler history prune failed")


def start_scheduler():
    """Idempotent — safe to call multiple times; second call is a no-op."""
    global _scheduler

    # Opt out in test runs and management commands where a background thread
    # would interfere or never get cleaned up.
    if os.environ.get('DISABLE_SCHEDULER', '').lower() in ('1', 'true', 'yes'):
        logger.info("DISABLE_SCHEDULER set — scheduler not started.")
        return

    if _scheduler is not None and _scheduler.running:
        return

    # Lazy imports so importing this module doesn't trigger Django ORM access
    # before apps are ready.
    from django_apscheduler.jobstores import DjangoJobStore

    _scheduler = BackgroundScheduler(timezone=SCHEDULER_TZ)
    _scheduler.add_jobstore(DjangoJobStore(), 'default')

    # Sync PENDING receipts every 2 minutes
    _scheduler.add_job(
        _run_sync_pending,
        trigger=CronTrigger(minute='*/2', timezone=SCHEDULER_TZ),
        id='sync_pending_receipts',
        name='Push PENDING FiscalReceipts to ZIMRA',
        max_instances=1,
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Daily state reconciliation at 04:00 CAT (low-traffic window)
    _scheduler.add_job(
        _run_daily_reconcile,
        trigger=CronTrigger(hour=4, minute=0, timezone=SCHEDULER_TZ),
        id='daily_reconcile_with_zimra',
        name='Sync local FiscalState with ZIMRA getStatus',
        max_instances=1,
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Prune job-execution history older than 30 days so the DB doesn't bloat.
    # Named function (not lambda) so it can be serialized by DjangoJobStore.
    _scheduler.add_job(
        _prune_history,
        trigger=CronTrigger(day_of_week='sun', hour=3, timezone=SCHEDULER_TZ),
        id='prune_apscheduler_history',
        name='Prune APScheduler job history',
        max_instances=1,
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("APScheduler started with %d jobs.", len(_scheduler.get_jobs()))
