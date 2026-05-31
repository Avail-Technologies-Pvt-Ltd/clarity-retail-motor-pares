"""
Open a fresh fiscal day, submit 3 distinct receipts, close the day,
and print the verification URL for each receipt that ZIMRA accepted cleanly.
"""

import os
import sys
import time
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'point_of_sale.settings_dev'
django.setup()

from decimal import Decimal
from django.test import Client

from fiscalisation import views as fv
from fiscalisation.services import zimra_now
from fiscalisation.models import (
    FiscalDevice, FiscalState, FiscalReceipt, FiscalDaySummary,
)


def hr(t=""):
    print("\n" + "=" * 60)
    if t:
        print(t)
        print("=" * 60)


client = Client(HTTP_HOST='localhost')
fd = FiscalDevice.objects.get(device_id='35454')
state = FiscalState.objects.get(device=fd)

hr("1. Status check (pre-open)")
resp = client.get('/fiscalisation/api/status/')
zs = resp.json()['response']
print(f"  ZIMRA: status={zs.get('fiscalDayStatus')} lastDay={zs.get('lastFiscalDayNo')} lastGlobal={zs.get('lastReceiptGlobalNo')}")

hr("2. Refresh applicable tax IDs from device")
resp = client.get('/fiscalisation/api/config/')
print(f"  applicableTaxes: {resp.json().get('applicableTaxes')}")

hr("3. Open day")
resp = client.get('/fiscalisation/api/open-day/')
print(f"  body: {resp.json()}")
state.refresh_from_db()
print(f"  local state -> day={state.fiscal_day_no} open={state.is_day_open} counter={state.receipt_counter} global={state.receipt_global_no} hash={state.last_receipt_hash}")

hr("4. Confirm day opened on ZIMRA")
resp = client.get('/fiscalisation/api/status/')
zs = resp.json()['response']
print(f"  ZIMRA: status={zs.get('fiscalDayStatus')} lastDay={zs.get('lastFiscalDayNo')}")
assert zs.get('fiscalDayStatus') == 'FiscalDayOpened', f"Day not opened: {zs}"

# Three distinct receipt scenarios
scenarios = [
    {
        "label": "single 15.5% line",
        "lines": [
            {"item_name": "Cooking Oil 750ml", "unit_price": "8.50", "quantity": "1",
             "tax_percent": 15.5, "hs_code": "15079090"},
        ],
        "payment_method": 0,  # cash
    },
    {
        "label": "mixed taxes + multi-line",
        "lines": [
            {"item_name": "Sugar 2kg",      "unit_price": "3.75", "quantity": "2",
             "tax_percent": 15.5, "hs_code": "17019910"},
            {"item_name": "Bread Loaf",     "unit_price": "1.50", "quantity": "3",
             "tax_percent": 0,    "hs_code": "19059090"},
            {"item_name": "Stamp",          "unit_price": "0.50", "quantity": "1",
             "tax_percent": "exempt", "hs_code": "49070010"},
        ],
        "payment_method": 1,  # card
    },
    {
        "label": "high-value single 15.5% line",
        "lines": [
            {"item_name": "Bicycle Helmet", "unit_price": "45.00", "quantity": "1",
             "tax_percent": 15.5, "hs_code": "65061010"},
        ],
        "payment_method": 0,
    },
]

submitted = []
hr("5. Submit 3 receipts")

for idx, scenario in enumerate(scenarios, start=1):
    if idx > 1:
        # ZIMRA's receipt-date format has no sub-second precision (spec uses
        # YYYY-MM-DDTHH:mm:ss) and RCPT030 fires if the new receipt date is
        # not strictly greater than the prior one. Wait 1.1s to guarantee a
        # different wall-clock second between back-to-back submissions.
        time.sleep(1.1)
    print(f"\n  --- Receipt {idx}/3: {scenario['label']} ---")

    state.refresh_from_db()
    next_counter = state.receipt_counter + 1
    next_global = state.receipt_global_no + 1
    receipt_dt = zimra_now()
    invoice_no = f"DEMO-D{state.fiscal_day_no}-{receipt_dt.strftime('%H%M%S')}-{next_global}"

    # Compute total from lines (tax-inclusive)
    total = sum(
        Decimal(line["unit_price"]) * Decimal(line["quantity"])
        for line in scenario["lines"]
    )

    receipt_data = {
        "receiptType": "FISCALINVOICE",
        "receiptCurrency": "USD",
        "receiptCounter": next_counter,
        "receiptGlobalNo": next_global,
        "invoiceNo": invoice_no,
        "receiptDate": receipt_dt,
        "receiptLines": scenario["lines"],
        "receiptPayments": [
            {"moneyTypeCode": scenario["payment_method"], "paymentAmount": float(total)},
        ],
    }

    prepared = fv.device.prepareReceipt(receipt_data, previousReceiptHash=state.last_receipt_hash)
    submit_resp = fv.device.submitReceipt(prepared)

    zimra_id = submit_resp.get('receiptID') if isinstance(submit_resp, dict) else None
    ve = submit_resp.get('validationErrors', []) if isinstance(submit_resp, dict) else []
    has_red = any(v.get('validationErrorColor') == 'Red' for v in ve)
    sync_status = 'FAILED' if has_red else ('SUCCESS' if zimra_id else 'PENDING')

    qr = fv.device.generate_qr_code(
        signature=prepared['receiptDeviceSignature']['signature'],
        receipt_global_no=prepared['receiptGlobalNo'],
        receipt_date=receipt_dt,
    )

    FiscalReceipt.objects.create(
        fiscal_state=state, fiscal_day_no=state.fiscal_day_no,
        receipt_global_no=prepared['receiptGlobalNo'],
        receipt_counter=next_counter,
        receipt_type='FISCALINVOICE',
        invoice_no=invoice_no,
        total_amount=Decimal(str(prepared['receiptTotal'])),
        local_hash=prepared['receiptDeviceSignature']['hash'],
        local_signature=prepared['receiptDeviceSignature']['signature'],
        qr_code_string=qr,
        prepared_payload=prepared,
        sync_status=sync_status,
        zimra_receipt_id=zimra_id,
        zimra_response_log=submit_resp if isinstance(submit_resp, dict) else {"raw": str(submit_resp)},
    )
    state.receipt_counter = next_counter
    state.receipt_global_no = next_global
    state.last_receipt_hash = prepared['receiptDeviceSignature']['hash']
    state.save()

    submitted.append({
        "scenario": scenario['label'],
        "invoice_no": invoice_no,
        "total": float(prepared['receiptTotal']),
        "zimra_id": zimra_id,
        "sync_status": sync_status,
        "validation_errors": ve,
        "qr_url": qr,
    })

    print(f"    invoiceNo  : {invoice_no}")
    print(f"    total      : {prepared['receiptTotal']} USD")
    print(f"    zimra_id   : {zimra_id}")
    print(f"    valErrors  : {ve}")
    print(f"    sync_status: {sync_status}")
    print(f"    URL        : {qr}")

hr("6. Close day")
resp = client.get('/fiscalisation/api/close-day/')
print(f"  body: {resp.json()}")

# Poll until ZIMRA confirms close (async)
hr("7. Poll ZIMRA close status")
for attempt in range(6):
    time.sleep(2)
    s = fv.device.getStatus()
    print(f"  attempt {attempt+1}: {s.get('fiscalDayStatus')} (errorCode={s.get('fiscalDayClosingErrorCode')})")
    if s.get('fiscalDayStatus') == 'FiscalDayClosed':
        break

hr("8. SUMMARY — Receipt verification URLs")
for r in submitted:
    status_marker = "OK " if r['sync_status'] == 'SUCCESS' and not r['validation_errors'] else "??"
    print(f"  [{status_marker}] {r['scenario']:35s}  ${r['total']:>8.2f}  zimra_id={r['zimra_id']}")
    print(f"        {r['qr_url']}")

print("\n[DONE]")
