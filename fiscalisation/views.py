# fiscalisation/views.py
import time
import threading
from collections import defaultdict
from datetime import datetime, date
from decimal import Decimal

from decouple import config
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

import os

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from .services import Device, zimra_now, register_new_device
from .models import FiscalDevice, FiscalState, FiscalReceipt, FiscalDaySummary, FiscalSettings
from .forms import FiscalDeviceForm, CertUploadForm


def _zimra_today():
    """Today's date in Zimbabwe local time (CAT)."""
    return zimra_now().date()


# Compact human-readable map of the ZIMRA validation error codes we surface.
# Source: Fiscal Device Gateway API v6.0 spec, section 7.3. We don't try to
# cover every code — just the ones that actually show up in practice and the
# common Red ones the operator needs to act on.
RCPT_CODE_EXPLANATIONS = {
    'RCPT010': 'Wrong currency code.',
    'RCPT011': 'Receipt counter is not sequential (must reset to 1 each day, then +1).',
    'RCPT012': 'Receipt global number is not sequential (must be +1 from prior).',
    'RCPT013': 'Invoice number is not unique for this taxpayer.',
    'RCPT014': 'Receipt date is earlier than fiscal day opening date — usually a clock-skew/timezone issue.',
    'RCPT015': 'Credit/debit note is missing the original-receipt reference.',
    'RCPT016': 'No receipt lines provided.',
    'RCPT017': 'No tax information provided.',
    'RCPT018': 'No payment information provided.',
    'RCPT019': 'Receipt total doesn’t equal sum of all receipt lines.',
    'RCPT020': 'Invoice signature is not valid — the device signature does not match what ZIMRA recomputed.',
    'RCPT021': 'VAT tax used but the taxpayer is not VAT-registered.',
    'RCPT029': 'CreditDebitNote object provided on a FiscalInvoice (should be on a CreditNote/DebitNote only).',
    'RCPT030': 'Receipt date earlier than a previously submitted receipt date — back-to-back receipts in the same wall-clock second.',
    'RCPT031': 'Receipt date is in the future.',
    'RCPT032': 'Credit/debit note refers to a non-existent original invoice.',
    'RCPT033': 'Credited/debited invoice was issued more than 12 months ago.',
    'RCPT034': 'Notes field is required on a credit/debit note but missing.',
    'RCPT035': 'Total credit-note amount exceeds the original invoice amount.',
    'RCPT036': 'Credit/debit note uses taxes that weren’t on the original invoice.',
    'RCPT037': 'Tax-exclusive: receipt total doesn’t equal sum(lines) + sum(taxes).',
    'RCPT038': 'Receipt total doesn’t equal sum of salesAmountWithTax across taxes.',
    'RCPT039': 'Receipt total doesn’t equal sum of all payment amounts.',
    'RCPT040': 'Receipt total must be ≥ 0 for FiscalInvoice/DebitNote; ≤ 0 for CreditNote.',
    'RCPT041': 'Receipt was submitted after fiscal day end.',
    'RCPT042': 'Credit/debit note currency differs from the original invoice.',
}


def _explain_rcpt_code(code):
    """Return the human description for a ZIMRA RCPTxxx code, or a placeholder."""
    if not code:
        return ''
    return RCPT_CODE_EXPLANATIONS.get(code, f'{code}: see ZIMRA Fiscal Device Gateway API v6.0 §7.3 for details.')


# ------------------------------------------------------------------
# DEVICE FACTORY
#
# Single source of truth = the FiscalDevice row with is_active=True.
# UI edits that row; we rebuild the live Device on demand. .env is only
# used to bootstrap an initial row if the DB is empty (so existing test
# installs keep working with their old .env).
# ------------------------------------------------------------------

_device_cache = {"obj": None, "device_id": None}
_device_lock = threading.Lock()


def _bootstrap_device_from_env_if_needed():
    """If no FiscalDevice row exists, create one from .env so first-run is painless."""
    if FiscalDevice.objects.exists():
        return
    try:
        FiscalDevice.objects.create(
            device_id=config('FISCAL_DEVICE_ID'),
            serial_no=config('FISCAL_SERIAL_NO'),
            activation_key=config('FISCAL_ACTIVATION_KEY'),
            cert_path=config('FISCAL_CERT_PATH', default='fiscalisation/certs/certificate.crt'),
            private_key_path=config('FISCAL_KEY_PATH', default='fiscalisation/certs/decrypted_key.key'),
            is_test_mode=config('FISCAL_TEST_MODE', default=True, cast=bool),
            company_name=config('FISCAL_COMPANY_NAME', default='Clarity Retail'),
            is_active=True,
        )
    except Exception:
        # No env at all — UI will create the first device manually
        pass


def get_device():
    """Return the live Device for the currently active FiscalDevice row.

    Cached for performance; cache invalidates on any FiscalDevice save
    (see post_save receiver below) or when the active row changes.
    """
    with _device_lock:
        _bootstrap_device_from_env_if_needed()
        try:
            fd = FiscalDevice.objects.get(is_active=True)
        except FiscalDevice.DoesNotExist:
            raise RuntimeError(
                "No active FiscalDevice configured. Use /fiscalisation/devices/ "
                "to add one and mark it active."
            )
        except FiscalDevice.MultipleObjectsReturned:
            # Recover gracefully: pick the most recently registered, deactivate others.
            fd = FiscalDevice.objects.filter(is_active=True).order_by('-registered_at').first()
            FiscalDevice.objects.exclude(pk=fd.pk).filter(is_active=True).update(is_active=False)

        cached = _device_cache["obj"]
        if cached is not None and _device_cache["device_id"] == fd.id:
            return cached

        device_obj = Device(
            device_id=fd.device_id,
            serialNo=fd.serial_no,
            activationKey=fd.activation_key,
            cert_path=fd.cert_path,
            private_key_path=fd.private_key_path,
            test_mode=fd.is_test_mode,
            deviceModelName=config('FISCAL_MODEL_NAME', default='Server'),
            deviceModelVersion=config('FISCAL_MODEL_VERSION', default='v1'),
            company_name=fd.company_name or 'Clarity Retail',
        )
        _device_cache["obj"] = device_obj
        _device_cache["device_id"] = fd.id
        return device_obj


def invalidate_device_cache():
    """Force get_device() to rebuild on next call. UI handlers call this after edits."""
    with _device_lock:
        _device_cache["obj"] = None
        _device_cache["device_id"] = None


@receiver(post_save, sender=FiscalDevice)
def _on_fiscal_device_saved(sender, instance, **kwargs):
    invalidate_device_cache()


class _DeviceProxy:
    """Module-level shim so existing `from fiscalisation.views import device`
    callsites keep working — every attribute access goes through get_device().
    Lets us swap underlying configuration from the UI without restarting Django.
    """

    def __getattr__(self, name):
        return getattr(get_device(), name)

    def __setattr__(self, name, value):
        setattr(get_device(), name, value)


device = _DeviceProxy()


def reconcile_with_zimra(fiscal_device=None):
    """Make the local FiscalState match ZIMRA's authoritative view.

    Use cases: operator closed the day manually on ZIMRA's portal, app
    crashed mid-close and the local DB is now ahead/behind, or a new app
    install needs to inherit existing device state.

    What it does (in order):
      1. Pulls getStatus from ZIMRA.
      2. Updates is_day_open, fiscal_day_no, receipt_global_no to match.
      3. If ZIMRA says the day is closed but locally we still have receipts
         marked PENDING for that day, we leave them alone (the sync worker
         will retry — they might still go through if the day reopens).
      4. Clears last_receipt_hash when transitioning closed -> closed
         (chain reset at day boundaries).

    Returns a dict describing what changed.
    """
    if fiscal_device is None:
        fiscal_device = FiscalDevice.objects.get(is_active=True)
    fiscal_state, _ = FiscalState.objects.get_or_create(device=fiscal_device)

    status = device.getStatus()
    if not isinstance(status, dict) or 'Error' in status or 'error' in status:
        return {"ok": False, "error": f"ZIMRA getStatus failed: {status}"}

    before = {
        "fiscal_day_no": fiscal_state.fiscal_day_no,
        "is_day_open": fiscal_state.is_day_open,
        "receipt_global_no": fiscal_state.receipt_global_no,
    }

    zimra_status = status.get('fiscalDayStatus')
    zimra_last_day = int(status.get('lastFiscalDayNo', fiscal_state.fiscal_day_no) or 0)
    zimra_last_global = int(status.get('lastReceiptGlobalNo', fiscal_state.receipt_global_no) or 0)

    # FiscalDayOpened means the *current* day is opened — fiscalDayNo in this
    # case is lastFiscalDayNo (the open one). For other statuses lastFiscalDayNo
    # is the most recent.
    fiscal_state.fiscal_day_no = zimra_last_day or fiscal_state.fiscal_day_no
    fiscal_state.is_day_open = (zimra_status == 'FiscalDayOpened')
    fiscal_state.receipt_global_no = max(zimra_last_global, fiscal_state.receipt_global_no)
    if not fiscal_state.is_day_open:
        # Chain hash resets at day boundary
        fiscal_state.last_receipt_hash = None
        fiscal_state.receipt_counter = 0
    fiscal_state.save()

    return {
        "ok": True,
        "zimra_status": zimra_status,
        "before": before,
        "after": {
            "fiscal_day_no": fiscal_state.fiscal_day_no,
            "is_day_open": fiscal_state.is_day_open,
            "receipt_global_no": fiscal_state.receipt_global_no,
        },
    }


def classify_submit_response(response):
    """Translate a ZIMRA submitReceipt response into a FiscalReceipt sync_status.

    Returns one of: 'SUCCESS', 'FAILED', 'PENDING'.

    Why this exists: ZIMRA returns HTTP 200 with a receiptID AND a
    receiptServerSignature even when validationErrors contains a Red entry.
    The day will then refuse to close until that receipt is dealt with. We
    used to mark these SUCCESS and only learned about the problem at close
    time. Now any Red validation = FAILED, surfaced immediately.

    See spec section 7.3 — Yellow is informational; Red is a hard rejection
    that blocks day close.
    """
    if not isinstance(response, dict):
        return 'PENDING'  # network/parse error — try again later
    if 'error' in response or 'Error' in response:
        return 'PENDING'  # transport-layer failure — retry later
    if response.get('receiptID') is None:
        return 'PENDING'  # malformed accept — retry
    validation_errors = response.get('validationErrors') or []
    if any(v.get('validationErrorColor') == 'Red' for v in validation_errors):
        return 'FAILED'
    return 'SUCCESS'




# -----------------------------------------
# PING
# -----------------------------------------

def ping_device(request):

    response = device.ping()

    return JsonResponse({
        "response": response
    })
# def ping_device(request):

#     try:

#         response = device.ping()

#         return JsonResponse({
#             "success": True,
#             "response": response
#         })

#     except Exception as e:

#         return JsonResponse({
#             "success": False,
#             "error": str(e)
#         }, status=500)


# -----------------------------------------
# GET CONFIG
# -----------------------------------------

def get_config(request):
    try:
        response = device.getConfig()

        # Sync the device's local tax-id map with whatever ZIMRA reports for
        # this device. This is what makes "test vs prod" a single env switch:
        # the tax IDs come from the device, not from hardcoded literals.
        applicable_taxes = None
        if isinstance(response, dict) and 'applicableTaxes' in response:
            try:
                applicable_taxes = device.refreshApplicableTaxes()
            except Exception:
                applicable_taxes = None  # don't fail get_config if mapping fails

        return JsonResponse({
            "success": True,
            "response": response,
            "applicableTaxes": applicable_taxes,
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


# -----------------------------------------
# GET STATUS
# -----------------------------------------

def get_status(request):

    try:

        response = device.getStatus()
>>>>>>> b7021b1903dd515c5dc82b4bfe13ca2982497309

        return JsonResponse({
            "success": True,
            "response": response
        })

    except Exception as e:

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


# -----------------------------------------
<<<<<<< HEAD
=======
# OPEN FISCAL DAY
# -----------------------------------------

@csrf_exempt
def open_day(request):
    try:
        fiscal_device = FiscalDevice.objects.get(is_active=True)
        fiscal_state, _ = FiscalState.objects.get_or_create(device=fiscal_device)

        if fiscal_state.is_day_open:
            return JsonResponse({
                "success": False,
                "error": f"Fiscal day {fiscal_state.fiscal_day_no} is already open."
            })

        # Ask ZIMRA what the last fiscal day number was; new day is +1.
        status = device.getStatus()
        if not isinstance(status, dict) or 'Error' in status or 'error' in status:
            return JsonResponse({
                "success": False,
                "error": f"Cannot read ZIMRA status: {status}"
            }, status=502)

        if status.get('fiscalDayStatus') != 'FiscalDayClosed':
            return JsonResponse({
                "success": False,
                "error": f"ZIMRA reports day status as {status.get('fiscalDayStatus')}; cannot open a new day until current one is closed."
            })

        next_fiscal_day_no = int(status.get('lastFiscalDayNo', 0)) + 1

        # Refuse to open a new day if the cert is about to expire — the
        # day might span a window where signatures suddenly stop verifying.
        cert_info = cert_expiry_info(fiscal_device.cert_path)
        if cert_info and cert_info.get('status') == 'critical':
            return JsonResponse({
                "success": False,
                "error": (
                    f"Device certificate expires in {cert_info.get('days_remaining')} day(s). "
                    "Renew the cert before opening a new fiscal day to avoid mid-day signature failures."
                ),
                "cert_expiry": cert_info,
            })

        # Sync tax IDs with the device's current config before opening.
        # ZIMRA can change tax rates/IDs between days; opening day is the
        # natural sync point.
        try:
            device.refreshApplicableTaxes()
        except Exception:
            pass  # non-fatal: device will fall back to defaults

        response = device.openDay(fiscalDayNo=next_fiscal_day_no)

        if isinstance(response, dict) and 'error' in response:
            return JsonResponse({"success": False, "error": response['error']})

        # Give ZIMRA's server a beat to register the open timestamp before
        # any receipts are submitted. Without this, the first receipt's
        # receiptDate can land in the same wall-clock second as the openDay
        # record, triggering RCPT014 ("receipt date earlier than fiscal day
        # opening date") and the cascading RCPT020 signature flag.
        # Opening a day is a once-per-day action, so 2s is invisible to users.
        time.sleep(2)

        # Persist local state (resets receipt_counter to 0; receipt_global_no
        # is cumulative across days and is left alone).
        fiscal_state.reset_for_new_day(next_fiscal_day_no, _zimra_today())

        return JsonResponse({"success": True, "response": response})

    except FiscalDevice.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "No active FiscalDevice configured in the database."
        }, status=500)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# -----------------------------------------
>>>>>>> b7021b1903dd515c5dc82b4bfe13ca2982497309
# TEST RECEIPT
# -----------------------------------------

@csrf_exempt
def test_receipt(request):

    try:

        mock_receipt = {

            "receiptType": "FISCALINVOICE",

            "receiptCurrency": "USD",

            "receiptCounter": 1,

            "receiptGlobalNo": 1,

            "invoiceNo": "INV-001",

<<<<<<< HEAD
            "receiptDate": datetime.now().strftime(
=======
            "receiptDate": zimra_now().strftime(
>>>>>>> b7021b1903dd515c5dc82b4bfe13ca2982497309
                '%Y-%m-%dT%H:%M:%S'
            ),

            "receiptLines": [

                {
                    "item_name": "Laptop",

                    "tax_percent": 15.5,

                    "quantity": 1,

                    "unit_price": 850.00
                },

                {
                    "item_name": "Mouse",

                    "tax_percent": 15.5,

                    "quantity": 2,

                    "unit_price": 25.00
                }

            ],

            "receiptPayments": [

                {
                    "moneyTypeCode": 0,
                    "paymentAmount": 900.00
                }

            ]
        }
<<<<<<< HEAD

        prepared_receipt = device.prepareReceipt(
            mock_receipt
        )

        response = device.submitReceipt(
            prepared_receipt
        )

        return JsonResponse({
            "success": True,
            "prepared_receipt": prepared_receipt,
            "zimra_response": response
        })

    except Exception as e:

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


# -----------------------------------------
# CLOSE DAY
# -----------------------------------------

@csrf_exempt
def close_day(request):

    try:

        response = device.closeDay(

            fiscalDayNo=1,

            fiscalDayDate=datetime.now().strftime('%Y-%m-%d'),

            lastReceiptCounterValue=1,

            fiscalDayCounters=[

                {
                    "fiscalCounterType": "SaleByTax",

                    "fiscalCounterCurrency": "USD",

                    "fiscalCounterTaxPercent": 15.5,

                    "fiscalCounterTaxID": 515,

                    "fiscalCounterValue": 900.00
                }

            ]
        )

        return JsonResponse({
            "success": True,
            "response": response
        })

    except Exception as e:

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)
=======

        prepared_receipt = device.prepareReceipt(
            mock_receipt
        )

        response = device.submitReceipt(
            prepared_receipt
        )

        return JsonResponse({
            "success": True,
            "prepared_receipt": prepared_receipt,
            "zimra_response": response
        })

    except Exception as e:

        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


# -----------------------------------------
# CLOSE DAY
# -----------------------------------------

def build_fiscal_day_counters(fiscal_state):
    """Aggregate FiscalReceipt payloads for the current day into the
    fiscalDayCounters array required by ZIMRA closeDay.

    Returns a list of counter dicts. Zero-value counters are excluded (services.py
    also filters them, but we drop them here for cleaner payloads in the summary).
    """
    receipts = FiscalReceipt.objects.filter(
        fiscal_state=fiscal_state,
        fiscal_day_no=fiscal_state.fiscal_day_no,
    )

    sale_by_tax = defaultdict(Decimal)
    sale_tax_by_tax = defaultdict(Decimal)
    credit_by_tax = defaultdict(Decimal)
    credit_tax_by_tax = defaultdict(Decimal)
    debit_by_tax = defaultdict(Decimal)
    debit_tax_by_tax = defaultdict(Decimal)
    balance_by_money = defaultdict(Decimal)

    for receipt in receipts:
        payload = receipt.prepared_payload or {}
        currency = payload.get('receiptCurrency', 'USD')
        rtype = (receipt.receipt_type or '').upper()

        for tl in payload.get('receiptTaxes', []):
            tax_id = tl.get('taxID')
            if tax_id is None:
                continue
            tax_pct = tl.get('taxPercent')  # None for exempt
            sales = Decimal(str(tl.get('salesAmountWithTax', 0)))
            tax_amt = Decimal(str(tl.get('taxAmount', 0)))
            key = (currency, int(tax_id), tax_pct)

            if rtype == 'FISCALINVOICE':
                sale_by_tax[key] += sales
                sale_tax_by_tax[key] += tax_amt
            elif rtype == 'CREDITNOTE':
                credit_by_tax[key] += sales
                credit_tax_by_tax[key] += tax_amt
            elif rtype == 'DEBITNOTE':
                debit_by_tax[key] += sales
                debit_tax_by_tax[key] += tax_amt

        for pmt in payload.get('receiptPayments', []):
            money_type = int(pmt.get('moneyTypeCode', 0))
            amt = Decimal(str(pmt.get('paymentAmount', 0)))
            key = (currency, money_type)
            if rtype == 'CREDITNOTE':
                balance_by_money[key] -= amt
            else:
                balance_by_money[key] += amt

    counters = []

    def add_tax_counter(ctype, accum):
        for (currency, tax_id, tax_pct), value in accum.items():
            if value == Decimal('0'):
                continue
            entry = {
                'fiscalCounterType': ctype,
                'fiscalCounterCurrency': currency,
                'fiscalCounterTaxID': tax_id,
                'fiscalCounterValue': float(value),
            }
            if tax_pct is not None:
                entry['fiscalCounterTaxPercent'] = float(tax_pct)
            counters.append(entry)

    add_tax_counter('SaleByTax', sale_by_tax)
    add_tax_counter('SaleTaxByTax', sale_tax_by_tax)
    add_tax_counter('CreditNoteByTax', credit_by_tax)
    add_tax_counter('CreditNoteTaxByTax', credit_tax_by_tax)
    add_tax_counter('DebitNoteByTax', debit_by_tax)
    add_tax_counter('DebitNoteTaxByTax', debit_tax_by_tax)

    for (currency, money_type), value in balance_by_money.items():
        if value == Decimal('0'):
            continue
        counters.append({
            'fiscalCounterType': 'BalanceByMoneyType',
            'fiscalCounterCurrency': currency,
            'fiscalCounterMoneyType': money_type,
            'fiscalCounterValue': float(value),
        })

    return counters


@csrf_exempt
def close_day(request):
    try:
        fiscal_device = FiscalDevice.objects.get(is_active=True)
        fiscal_state = FiscalState.objects.get(device=fiscal_device)

        if not fiscal_state.is_day_open:
            return JsonResponse({
                "success": False,
                "error": "No fiscal day is currently open."
            })

        # ZIMRA will fail the close (status=FiscalDayCloseFailed,
        # errorCode=ReceiptsWithValidationErrors) if any receipt in this day
        # is invalid or wasn't successfully submitted. Catch this locally
        # before we send a doomed closeDay request — and give the operator a
        # clear list of what to address.
        bad = list(
            FiscalReceipt.objects
            .filter(
                fiscal_state=fiscal_state,
                fiscal_day_no=fiscal_state.fiscal_day_no,
                sync_status__in=['PENDING', 'FAILED'],
            )
            .values('invoice_no', 'receipt_global_no', 'sync_status', 'zimra_receipt_id')
        )
        if bad:
            return JsonResponse({
                "success": False,
                "error": (
                    "Cannot close day — there are receipts that ZIMRA either "
                    "rejected (FAILED) or hasn't acknowledged yet (PENDING). "
                    "Resolve them first (retry sync, void, or contact ZIMRA)."
                ),
                "blocking_receipts": bad,
            })

        counters = build_fiscal_day_counters(fiscal_state)
        fiscal_day_date = str(fiscal_state.current_day_date or _zimra_today())

        # Total sales for the summary (sum of sales-with-tax across FISCALINVOICEs)
        total_sales = sum(
            (Decimal(str(c['fiscalCounterValue'])) for c in counters
             if c['fiscalCounterType'] == 'SaleByTax'),
            Decimal('0'),
        )

        response = device.closeDay(
            fiscalDayNo=fiscal_state.fiscal_day_no,
            fiscalDayDate=fiscal_day_date,
            lastReceiptCounterValue=fiscal_state.receipt_counter,
            fiscalDayCounters=counters,
        )

        closed_ok = (
            isinstance(response, dict)
            and 'error' not in response
            and 'Error' not in response
        )

        FiscalDaySummary.objects.update_or_create(
            fiscal_state=fiscal_state,
            fiscal_day_no=fiscal_state.fiscal_day_no,
            defaults={
                'day_date': fiscal_state.current_day_date or _zimra_today(),
                'total_receipts_processed': fiscal_state.receipt_counter,
                'total_sales_value': total_sales,
                'closing_counters_payload': counters,
                'closing_response': response if isinstance(response, dict) else {"raw": str(response)},
                'is_closed_successfully': closed_ok,
            },
        )

        if closed_ok:
            fiscal_state.is_day_open = False
            fiscal_state.save(update_fields=['is_day_open', 'updated_at'])

        return JsonResponse({"success": closed_ok, "response": response})

    except FiscalDevice.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "No active FiscalDevice configured in the database."
        }, status=500)
    except FiscalState.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "FiscalState row missing for the active device."
        }, status=500)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# -----------------------------------------
# DASHBOARD (UI + DATA)
# -----------------------------------------

def dashboard(request):
    return render(request, 'fiscalisation/dashboard.html')


@csrf_exempt
def pause_fiscalization(request):
    """Halt all ZIMRA signing/submission. Checkout continues, prints have no QR."""
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "POST only."}, status=405)
    import json as _json
    try:
        body = _json.loads(request.body or b'{}')
    except Exception:
        body = {}
    reason = body.get('reason', 'other')
    notes = (body.get('notes') or '').strip()

    settings_obj = FiscalSettings.get()
    settings_obj.fiscalization_paused = True
    # tz-aware CAT so Django stores the right UTC instant
    settings_obj.paused_at = zimra_now().replace(tzinfo=_ZIMBABWE_TZ)
    settings_obj.paused_reason = reason if reason in dict(FiscalSettings.PAUSE_REASON_CHOICES) else 'other'
    settings_obj.paused_notes = notes
    settings_obj.save()
    return JsonResponse({
        "success": True,
        "fiscalization_paused": True,
        "paused_at": settings_obj.paused_at.isoformat() if settings_obj.paused_at else None,
        "reason": settings_obj.paused_reason,
        "notes": settings_obj.paused_notes,
    })


@csrf_exempt
def resume_fiscalization(request):
    """Re-enable ZIMRA signing/submission."""
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "POST only."}, status=405)
    settings_obj = FiscalSettings.get()
    settings_obj.fiscalization_paused = False
    settings_obj.paused_at = None
    settings_obj.paused_reason = ''
    settings_obj.paused_notes = ''
    settings_obj.save()
    return JsonResponse({"success": True, "fiscalization_paused": False})


@csrf_exempt
def sync_pending_now(request):
    """One-shot sync of PENDING receipts, triggered from UI."""
    from django.core.management import call_command
    import io
    buf = io.StringIO()
    try:
        call_command('sync_pending_receipts', stdout=buf, stderr=buf)
        return JsonResponse({"success": True, "log": buf.getvalue()})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e), "log": buf.getvalue()}, status=500)


@csrf_exempt
def reconcile(request):
    """Force-sync local FiscalState to whatever ZIMRA's getStatus reports."""
    try:
        result = reconcile_with_zimra()
        return JsonResponse({"success": result.get("ok", False), **result})
    except FiscalDevice.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "No active FiscalDevice configured in the database."
        }, status=500)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def dashboard_data(request):
    """Single endpoint backing the dashboard. Returns everything the UI needs
    in one round-trip: device + day state + receipt counts + recent + failed
    list (with ZIMRA validation codes/colours expanded) + pause state.
    """
    # Pause state is always reportable, even with no device configured.
    settings_obj = FiscalSettings.get()
    pause_block = {
        "fiscalization_paused": settings_obj.fiscalization_paused,
        "paused_at": settings_obj.paused_at.isoformat() if settings_obj.paused_at else None,
        "paused_reason": settings_obj.paused_reason,
        "paused_reason_label": dict(FiscalSettings.PAUSE_REASON_CHOICES).get(settings_obj.paused_reason, ''),
        "paused_notes": settings_obj.paused_notes,
    }

    try:
        fiscal_device = FiscalDevice.objects.get(is_active=True)
    except FiscalDevice.DoesNotExist:
        return JsonResponse({
            "success": True,
            "configured": False,
            "pause": pause_block,
            "message": "No active FiscalDevice. Add one at /fiscalisation/devices/",
        })

    fiscal_state, _ = FiscalState.objects.get_or_create(device=fiscal_device)

    # Receipt sync-status counts (current day + lifetime)
    today_receipts = FiscalReceipt.objects.filter(
        fiscal_state=fiscal_state,
        fiscal_day_no=fiscal_state.fiscal_day_no,
    )
    today_counts = {
        'success': today_receipts.filter(sync_status='SUCCESS').count(),
        'pending': today_receipts.filter(sync_status='PENDING').count(),
        'failed':  today_receipts.filter(sync_status='FAILED').count(),
        'total':   today_receipts.count(),
    }
    all_receipts = FiscalReceipt.objects.filter(fiscal_state=fiscal_state)
    lifetime_counts = {
        'success': all_receipts.filter(sync_status='SUCCESS').count(),
        'pending': all_receipts.filter(sync_status='PENDING').count(),
        'failed':  all_receipts.filter(sync_status='FAILED').count(),
        'total':   all_receipts.count(),
    }

    # Failed receipts — surface the ZIMRA validation codes + colours so the
    # operator knows what was wrong and which one to escalate.
    failed_qs = (
        FiscalReceipt.objects
        .filter(fiscal_state=fiscal_state, sync_status='FAILED')
        .order_by('-created_at')[:20]
    )
    failed_list = []
    for r in failed_qs:
        ve = (r.zimra_response_log or {}).get('validationErrors') or []
        failed_list.append({
            'invoice_no': r.invoice_no,
            'fiscal_day_no': r.fiscal_day_no,
            'receipt_global_no': r.receipt_global_no,
            'total_amount': float(r.total_amount),
            'created_at': r.created_at.isoformat(),
            'zimra_receipt_id': r.zimra_receipt_id,
            'validation_errors': [
                {
                    'code': v.get('validationErrorCode'),
                    'colour': v.get('validationErrorColor'),
                    'explain': _explain_rcpt_code(v.get('validationErrorCode', '')),
                }
                for v in ve
            ],
            'qr_url': r.qr_code_string,
        })

    pending_qs = (
        FiscalReceipt.objects
        .filter(fiscal_state=fiscal_state, sync_status='PENDING')
        .order_by('-created_at')[:20]
    )
    pending_list = [
        {
            'invoice_no': r.invoice_no,
            'fiscal_day_no': r.fiscal_day_no,
            'receipt_global_no': r.receipt_global_no,
            'total_amount': float(r.total_amount),
            'created_at': r.created_at.isoformat(),
            'last_error': (r.zimra_response_log or {}).get('error') or '(awaiting first submit)',
        }
        for r in pending_qs
    ]

    recent_receipts = (
        FiscalReceipt.objects
        .filter(fiscal_state=fiscal_state)
        .order_by('-created_at')[:15]
    )
    recent_list = [
        {
            'invoice_no': r.invoice_no,
            'fiscal_day_no': r.fiscal_day_no,
            'receipt_global_no': r.receipt_global_no,
            'total_amount': float(r.total_amount),
            'sync_status': r.sync_status,
            'created_at': r.created_at.isoformat(),
            'qr_url': r.qr_code_string,
        }
        for r in recent_receipts
    ]

    summaries = (
        FiscalDaySummary.objects
        .filter(fiscal_state=fiscal_state)
        .order_by('-fiscal_day_no')[:10]
    )
    summaries_list = [
        {
            'fiscal_day_no': s.fiscal_day_no,
            'day_date': str(s.day_date),
            'total_receipts_processed': s.total_receipts_processed,
            'total_sales_value': float(s.total_sales_value),
            'is_closed_successfully': s.is_closed_successfully,
            'closed_at': s.closed_at.isoformat() if s.closed_at else None,
            'closing_response': s.closing_response,
        }
        for s in summaries
    ]

    return JsonResponse({
        "success": True,
        "configured": True,
        "pause": pause_block,
        "device": {
            "device_id": fiscal_device.device_id,
            "serial_no": fiscal_device.serial_no,
            "company": fiscal_device.company_name,
            "test_mode": fiscal_device.is_test_mode,
            "cert_expiry": cert_expiry_info(fiscal_device.cert_path),
        },
        "state": {
            "fiscal_day_no": fiscal_state.fiscal_day_no,
            "is_day_open": fiscal_state.is_day_open,
            "receipt_counter": fiscal_state.receipt_counter,
            "receipt_global_no": fiscal_state.receipt_global_no,
            "current_day_date": str(fiscal_state.current_day_date) if fiscal_state.current_day_date else None,
            "day_opened_at": fiscal_state.day_opened_at.isoformat() if fiscal_state.day_opened_at else None,
            **_day_age_summary(fiscal_state),
        },
        "counts": {
            "today": today_counts,
            "lifetime": lifetime_counts,
        },
        "recent_receipts": recent_list,
        "failed_receipts": failed_list,
        "pending_receipts": pending_list,
        "day_summaries": summaries_list,
    })

# ===================================================================
# DEVICE MANAGEMENT UI
# Reseller-facing screens. No env editing required for a new device.
# ===================================================================

CERTS_BASE_DIR = 'fiscalisation/certs'


def _device_cert_dir(device_id):
    """Each device gets its own cert folder so multiple devices coexist."""
    path = os.path.join(CERTS_BASE_DIR, str(device_id))
    os.makedirs(path, exist_ok=True)
    return path


def cert_expiry_info(cert_path):
    """Read a PEM cert and return {expires_at, days_remaining, status}.

    Status thresholds:
      ok       — more than 30 days left
      warning  — between 7 and 30 days left
      critical — less than 7 days OR already expired

    Returns None if cert file doesn't exist or can't be parsed.
    """
    if not cert_path or not os.path.exists(cert_path):
        return None
    try:
        from cryptography import x509
        with open(cert_path, 'rb') as f:
            cert = x509.load_pem_x509_certificate(f.read())
        # Prefer the UTC-aware accessor where available
        try:
            expires_at = cert.not_valid_after_utc
        except AttributeError:
            expires_at = cert.not_valid_after
        # Compare in CAT to keep all "today" references consistent
        from datetime import timezone as _tz
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=_tz.utc)
        now_aware = zimra_now().replace(tzinfo=_ZIMBABWE_TZ)
        delta = expires_at - now_aware
        days = delta.days
        if days <= 7:
            status = 'critical'
        elif days <= 30:
            status = 'warning'
        else:
            status = 'ok'
        return {
            'expires_at': expires_at.isoformat(),
            'days_remaining': days,
            'status': status,
        }
    except Exception as e:
        return {'error': str(e), 'status': 'unreadable'}


# Re-import _ZIMBABWE_TZ at module level for cert_expiry_info
from .services import _ZIMBABWE_TZ  # noqa: E402


# Cache the per-device fiscal-day limits (pulled from getConfig).
# These rarely change so caching them avoids hitting ZIMRA on every dashboard tick.
_day_limits_cache = {}  # device_id -> {'max_hours': int, 'notify_hours': int}


def _get_day_limits(device_obj):
    """Return {'max_hours': N, 'notify_hours': M} for the device.

    Tries the cache first; falls back to a fresh getConfig; defaults to
    24/2 (ZIMRA's standard) if everything fails so we never block on it.
    """
    dev_id = device_obj.deviceID
    if dev_id in _day_limits_cache:
        return _day_limits_cache[dev_id]
    limits = {'max_hours': 24, 'notify_hours': 2}
    try:
        cfg = device_obj.getConfig()
        if isinstance(cfg, dict):
            limits['max_hours'] = int(cfg.get('taxPayerDayMaxHrs', 24))
            limits['notify_hours'] = int(cfg.get('taxpayerDayEndNotificationHrs', 2))
            _day_limits_cache[dev_id] = limits
    except Exception:
        pass
    return limits


def _day_age_summary(fiscal_state):
    """How long has the current fiscal day been open?

    Returns a dict that goes straight into the dashboard JSON. Status:
        ok       — well within the max-hours window
        warning  — inside the notification window (taxpayerDayEndNotificationHrs
                   before the cap)
        critical — past the cap; ZIMRA will refuse new receipts soon and the
                   day will need an emergency close
    """
    if not fiscal_state.is_day_open or not fiscal_state.day_opened_at:
        return {
            'hours_open': None,
            'max_hours': None,
            'notify_at_hours': None,
            'day_age_status': 'ok',
        }
    try:
        limits = _get_day_limits(get_device())
    except Exception:
        limits = {'max_hours': 24, 'notify_hours': 2}

    opened = fiscal_state.day_opened_at
    if opened.tzinfo is None:
        opened = opened.replace(tzinfo=_ZIMBABWE_TZ)
    now_aware = zimra_now().replace(tzinfo=_ZIMBABWE_TZ)
    hours_open = (now_aware - opened).total_seconds() / 3600

    notify_at = limits['max_hours'] - limits['notify_hours']
    if hours_open >= limits['max_hours']:
        status = 'critical'
    elif hours_open >= notify_at:
        status = 'warning'
    else:
        status = 'ok'

    return {
        'hours_open': round(hours_open, 1),
        'max_hours': limits['max_hours'],
        'notify_at_hours': notify_at,
        'day_age_status': status,
    }


def device_list(request):
    devices = FiscalDevice.objects.all().order_by('-is_active', '-registered_at')
    rows = []
    for d in devices:
        rows.append({
            'obj': d,
            'has_cert': os.path.exists(d.cert_path) if d.cert_path else False,
            'has_key': os.path.exists(d.private_key_path) if d.private_key_path else False,
            'cert_expiry': cert_expiry_info(d.cert_path),
            'state': getattr(d, 'state', None),
        })
    return render(request, 'fiscalisation/devices/list.html', {'rows': rows})


def device_add(request):
    if request.method == 'POST':
        form = FiscalDeviceForm(request.POST)
        if form.is_valid():
            fd = form.save(commit=False)
            cert_dir = _device_cert_dir(fd.device_id)
            fd.cert_path = os.path.join(cert_dir, 'certificate.crt')
            fd.private_key_path = os.path.join(cert_dir, 'decrypted_key.key')
            fd.is_active = False
            fd.save()
            FiscalState.objects.get_or_create(device=fd)
            messages.success(request, f"Device {fd.device_id} added. Next: register with ZIMRA or upload existing certs.")
            return redirect(reverse('fiscal_device_detail', args=[fd.pk]))
    else:
        form = FiscalDeviceForm()
    return render(request, 'fiscalisation/devices/form.html', {'form': form, 'mode': 'add'})


def device_detail(request, pk):
    fd = FiscalDevice.objects.get(pk=pk)
    has_cert = os.path.exists(fd.cert_path) if fd.cert_path else False
    has_key = os.path.exists(fd.private_key_path) if fd.private_key_path else False
    upload_form = CertUploadForm()
    return render(request, 'fiscalisation/devices/detail.html', {
        'device': fd,
        'has_cert': has_cert,
        'has_key': has_key,
        'cert_expiry': cert_expiry_info(fd.cert_path),
        'upload_form': upload_form,
    })


@csrf_exempt
def device_register_with_zimra(request, pk):
    """Generate a CSR, send to ZIMRA, save the issued cert. One-shot, no fiddling."""
    fd = FiscalDevice.objects.get(pk=pk)
    cert_dir = _device_cert_dir(fd.device_id)
    try:
        register_new_device(
            fiscal_device_serial_no=fd.serial_no,
            device_id=fd.device_id,
            activation_key=fd.activation_key,
            model_name=config('FISCAL_MODEL_NAME', default='Server'),
            folder_name=cert_dir,
            certificate_filename='certificate',
            private_key_filename='decrypted_key',
            prod=not fd.is_test_mode,
        )
        fd.cert_path = os.path.join(cert_dir, 'certificate.crt')
        fd.private_key_path = os.path.join(cert_dir, 'decrypted_key.key')
        fd.save()
        messages.success(request, f"Device {fd.device_id} registered with ZIMRA and cert saved.")
    except Exception as e:
        messages.error(request, f"Registration failed: {e}")
    return redirect(reverse('fiscal_device_detail', args=[fd.pk]))


@csrf_exempt
def device_upload_cert(request, pk):
    fd = FiscalDevice.objects.get(pk=pk)
    if request.method != 'POST':
        return redirect(reverse('fiscal_device_detail', args=[fd.pk]))
    form = CertUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Cert + key are both required.")
        return redirect(reverse('fiscal_device_detail', args=[fd.pk]))

    cert_dir = _device_cert_dir(fd.device_id)
    cert_path = os.path.join(cert_dir, 'certificate.crt')
    key_path = os.path.join(cert_dir, 'decrypted_key.key')
    with open(cert_path, 'wb') as f:
        for chunk in form.cleaned_data['certificate'].chunks():
            f.write(chunk)
    with open(key_path, 'wb') as f:
        for chunk in form.cleaned_data['private_key'].chunks():
            f.write(chunk)
    fd.cert_path = cert_path
    fd.private_key_path = key_path
    fd.save()
    messages.success(request, f"Cert + key uploaded for {fd.device_id}.")
    return redirect(reverse('fiscal_device_detail', args=[fd.pk]))


@csrf_exempt
def device_set_active(request, pk):
    """Atomically flip is_active so exactly one device is active at a time."""
    fd = FiscalDevice.objects.get(pk=pk)
    FiscalDevice.objects.exclude(pk=fd.pk).update(is_active=False)
    fd.is_active = True
    fd.save()
    invalidate_device_cache()
    messages.success(request, f"Device {fd.device_id} is now active.")
    return redirect(reverse('fiscal_device_list'))


@csrf_exempt
def device_test(request, pk):
    """Ping + getStatus + getConfig for one specific device — diagnostic shortcut."""
    fd = FiscalDevice.objects.get(pk=pk)
    try:
        tmp_device = Device(
            device_id=fd.device_id, serialNo=fd.serial_no, activationKey=fd.activation_key,
            cert_path=fd.cert_path, private_key_path=fd.private_key_path,
            test_mode=fd.is_test_mode,
            company_name=fd.company_name or 'Clarity Retail',
        )
        ping = tmp_device.ping()
        status = tmp_device.getStatus()
        config_data = tmp_device.getConfig()
        return JsonResponse({
            "success": True,
            "device": {"id": fd.device_id, "company": fd.company_name, "test_mode": fd.is_test_mode},
            "ping": ping,
            "status": status,
            "config": config_data,
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
def device_delete(request, pk):
    if request.method != 'POST':
        return redirect(reverse('fiscal_device_list'))
    fd = FiscalDevice.objects.get(pk=pk)
    if fd.is_active:
        messages.error(request, "Cannot delete the active device. Set another active first.")
        return redirect(reverse('fiscal_device_list'))
    name = str(fd)
    fd.delete()
    invalidate_device_cache()
    messages.success(request, f"Deleted {name}.")
    return redirect(reverse('fiscal_device_list'))
>>>>>>> b7021b1903dd515c5dc82b4bfe13ca2982497309
