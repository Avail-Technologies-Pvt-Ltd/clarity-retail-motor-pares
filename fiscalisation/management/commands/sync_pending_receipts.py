"""
Background-style sync worker: push PENDING receipts up to ZIMRA.

Usage:
    python manage.py sync_pending_receipts            # one pass
    python manage.py sync_pending_receipts --watch    # loop every N seconds
    python manage.py sync_pending_receipts --watch --interval 30
    python manage.py sync_pending_receipts --include-failed   # also retry FAILED (rare)

Cron suggestion (every 2 minutes):
    */2 * * * * cd /path/to/app && /path/to/.venv/bin/python manage.py sync_pending_receipts

Design notes:
  * Only PENDING is retried by default. FAILED means ZIMRA actively rejected it
    (e.g. RCPT020 — bad signature, RCPT030 — bad date); retrying with the same
    payload will fail the same way. Surface those to the operator instead.
  * Receipts are sent in (fiscal_day_no, receipt_global_no) order — ZIMRA
    enforces monotonic globalNo and chained signatures.
  * Same ≥1s spacing rule as the POS (RCPT030: two receipts in same wall-clock
    second are rejected). We sleep between sends.
  * If the device is unreachable for a given receipt, we leave it PENDING and
    move on; next run picks up where we left off.
"""

import time
import logging

from django.core.management.base import BaseCommand

from fiscalisation.models import FiscalReceipt
from fiscalisation.views import get_device, classify_submit_response


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Submit PENDING (and optionally FAILED) FiscalReceipts to ZIMRA."

    def add_arguments(self, parser):
        parser.add_argument('--watch', action='store_true',
                            help="Loop forever instead of single pass.")
        parser.add_argument('--interval', type=int, default=60,
                            help="Seconds between passes when --watch is set.")
        parser.add_argument('--include-failed', action='store_true',
                            help="Also retry FAILED receipts (use with caution — usually a config issue).")
        parser.add_argument('--max-per-pass', type=int, default=500,
                            help="Cap per pass to avoid hammering ZIMRA.")
        parser.add_argument('--spacing', type=float, default=1.1,
                            help="Seconds between submissions to satisfy ZIMRA's second-precision receiptDate rule.")

    def handle(self, *args, **opts):
        watch = opts['watch']
        interval = opts['interval']
        include_failed = opts['include_failed']
        max_per_pass = opts['max_per_pass']
        spacing = opts['spacing']

        statuses = ['PENDING'] + (['FAILED'] if include_failed else [])

        while True:
            pending = list(
                FiscalReceipt.objects
                .filter(sync_status__in=statuses)
                .order_by('fiscal_day_no', 'receipt_global_no')[:max_per_pass]
            )
            if pending:
                self.stdout.write(f"Found {len(pending)} receipt(s) to submit. (statuses={statuses})")
                try:
                    device = get_device()
                except Exception as e:
                    self.stderr.write(f"Cannot build Device: {e}")
                    if not watch:
                        return
                    time.sleep(interval)
                    continue

                for idx, r in enumerate(pending):
                    if idx > 0:
                        time.sleep(spacing)
                    self._submit_one(device, r)
            else:
                self.stdout.write("No pending receipts.")

            if not watch:
                return
            time.sleep(interval)

    def _submit_one(self, device, receipt):
        try:
            resp = device.submitReceipt(receipt.prepared_payload)
            new_status = classify_submit_response(resp)
            receipt.sync_status = new_status
            if isinstance(resp, dict):
                receipt.zimra_receipt_id = resp.get('receiptID') or receipt.zimra_receipt_id
                receipt.zimra_response_log = resp
            receipt.save(update_fields=['sync_status', 'zimra_receipt_id', 'zimra_response_log'])
            self.stdout.write(
                f"  day={receipt.fiscal_day_no} global={receipt.receipt_global_no} "
                f"inv={receipt.invoice_no} -> {new_status} "
                f"(zimra_id={receipt.zimra_receipt_id})"
            )
        except Exception as e:
            # Transport error: leave PENDING, log and move on.
            logger.warning("sync failed for receipt %s: %s", receipt.invoice_no, e)
            self.stderr.write(
                f"  day={receipt.fiscal_day_no} global={receipt.receipt_global_no} "
                f"inv={receipt.invoice_no} -> transport error: {e}"
            )
