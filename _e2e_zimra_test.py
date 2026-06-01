"""
End-to-end fiscal cycle test against ZIMRA test environment.
Runs: getStatus -> openDay -> sign+submit a 0% sale -> closeDay.

The new test device 35453 only has tax 0% (taxID 513), so we use a 0% receipt.
"""

import os
import sys
import time
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'point_of_sale.settings_dev'
django.setup()

from datetime import datetime, date
from fiscalisation.services import zimra_now
from decimal import Decimal
from django.test import Client

from fiscalisation import views as fv
from fiscalisation.models import (
    FiscalDevice, FiscalState, FiscalReceipt, FiscalDaySummary
)


def hr(title=""):
    print("\n" + "=" * 60)
    if title:
        print(title)
        print("=" * 60)


hr("0. Sync DB FiscalDevice + FiscalState with .env device")
device_row, created = FiscalDevice.objects.update_or_create(
    device_id='35454',
    defaults={
        'serial_no': 'testserial2',
        'activation_key': '00832487',
        'company_name': 'TEST CAMP 1',
        'is_test_mode': True,
        'is_active': True,
        'cert_path': 'fiscalisation/certs/certificate.crt',
        'private_key_path': 'fiscalisation/certs/decrypted_key.key',
    },
)
# Make sure no other device row is competing for is_active=True
FiscalDevice.objects.exclude(pk=device_row.pk).update(is_active=False)
state, _ = FiscalState.objects.get_or_create(device=device_row)
print(f"  FiscalDevice: id={device_row.id} created={created} device_id={device_row.device_id}")
print(f"  FiscalState : day={state.fiscal_day_no} open={state.is_day_open} counter={state.receipt_counter} global={state.receipt_global_no}")

client = Client(HTTP_HOST='localhost')

hr("1. /api/ping/")
resp = client.get('/fiscalisation/api/ping/')
print(f"  status={resp.status_code} body={resp.json()}")
assert resp.status_code == 200

hr("2. /api/config/  (refreshes tax IDs)")
resp = client.get('/fiscalisation/api/config/')
data = resp.json()
print(f"  status={resp.status_code}")
print(f"  applicableTaxes pulled from device: {data.get('applicableTaxes')}")
assert resp.status_code == 200
assert data['success'] is True

# Confirm the in-process device has the live tax mapping now
print(f"  fv.device.applicableTaxes (in-process): {fv.device.applicableTaxes}")

hr("3. /api/status/")
resp = client.get('/fiscalisation/api/status/')
data = resp.json()
print(f"  status={resp.status_code} body={data}")
zimra_status = data.get('response', {})
print(f"  fiscalDayStatus: {zimra_status.get('fiscalDayStatus')}")
print(f"  lastFiscalDayNo: {zimra_status.get('lastFiscalDayNo')}")

hr("4. /api/open-day/  (state may already be FiscalDayOpen on ZIMRA)")
# If our local state thinks day is open, sync it down first based on ZIMRA's view
if zimra_status.get('fiscalDayStatus') == 'FiscalDayOpened':
    print("  (skipping openDay — ZIMRA reports day already open; reusing it)")
    last_day_no = int(zimra_status.get('lastFiscalDayNo', 1))
    state.fiscal_day_no = last_day_no
    state.is_day_open = True
    state.current_day_date = zimra_now().date()
    state.save()
else:
    resp = client.get('/fiscalisation/api/open-day/')
    data = resp.json()
    print(f"  status={resp.status_code} body={data}")
    state.refresh_from_db()
    print(f"  FiscalState now: day={state.fiscal_day_no} open={state.is_day_open}")

hr("4.5 Wait 2s for ZIMRA to settle, then re-check status")
time.sleep(2)
resp = client.get('/fiscalisation/api/status/')
post_open_status = resp.json().get('response', {})
print(f"  fiscalDayStatus={post_open_status.get('fiscalDayStatus')} lastFiscalDayNo={post_open_status.get('lastFiscalDayNo')}")
assert post_open_status.get('fiscalDayStatus') == 'FiscalDayOpened', \
    f"Day is not Opened on ZIMRA side: {post_open_status}"

hr("5. Build receipt and submit it")
state.refresh_from_db()  # pick up cleared last_receipt_hash from openDay
next_counter = state.receipt_counter + 1
next_global = state.receipt_global_no + 1
invoice_no = f"E2E-{zimra_now().strftime('%H%M%S')}-{next_global}"

receipt_data = {
    "receiptType": "FISCALINVOICE",
    "receiptCurrency": "USD",
    "receiptCounter": next_counter,
    "receiptGlobalNo": next_global,
    "invoiceNo": invoice_no,
    "receiptDate": zimra_now(),
    "receiptLines": [
        # tax-inclusive prices; mix of standard 15.5%, zero-rated, and exempt
        {"item_name": "Bread Loaf", "unit_price": "11.55", "quantity": "1", "tax_percent": 15.5, "hs_code": "04021099"},
        {"item_name": "Milk 1L", "unit_price": "5.00", "quantity": "2", "tax_percent": 0, "hs_code": "04021099"},
        {"item_name": "Postage Stamp", "unit_price": "2.00", "quantity": "1", "tax_percent": "exempt", "hs_code": "04021099"},
    ],
    "receiptPayments": [
        # 11.55 + 10.00 + 2.00 = 23.55
        {"moneyTypeCode": 0, "paymentAmount": 23.55},
    ],
}
print(f"  invoice_no={invoice_no} counter={next_counter} global={next_global}")

prepared = fv.device.prepareReceipt(receipt_data, previousReceiptHash=state.last_receipt_hash)
print(f"  prepared receiptTotal={prepared['receiptTotal']}")
print(f"  prepared receiptTaxes={prepared['receiptTaxes']}")
print(f"  signature hash={prepared['receiptDeviceSignature']['hash'][:32]}...")

submit_response = fv.device.submitReceipt(prepared)
print(f"  submitReceipt response: {submit_response}")

# Save to FiscalReceipt and bump state
qr = fv.device.generate_qr_code(
    signature=prepared['receiptDeviceSignature']['signature'],
    receipt_global_no=prepared['receiptGlobalNo'],
    receipt_date=zimra_now(),
)
zimra_id = submit_response.get('receiptID') if isinstance(submit_response, dict) else None
sync_status = 'SUCCESS' if zimra_id else 'FAILED'

FiscalReceipt.objects.create(
    fiscal_state=state,
    fiscal_day_no=state.fiscal_day_no,
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
    zimra_response_log=submit_response if isinstance(submit_response, dict) else {"raw": str(submit_response)},
)
state.receipt_counter = next_counter
state.receipt_global_no = next_global
state.last_receipt_hash = prepared['receiptDeviceSignature']['hash']
state.save()
print(f"  Saved FiscalReceipt -> sync_status={sync_status} zimra_id={zimra_id}")

hr("6. /api/close-day/")
resp = client.get('/fiscalisation/api/close-day/')
data = resp.json()
print(f"  status={resp.status_code} body={data}")

state.refresh_from_db()
print(f"  FiscalState after close: day={state.fiscal_day_no} open={state.is_day_open}")

summary = FiscalDaySummary.objects.filter(fiscal_state=state, fiscal_day_no=state.fiscal_day_no).first()
if summary:
    print(f"  FiscalDaySummary: closed_ok={summary.is_closed_successfully} receipts={summary.total_receipts_processed} sales={summary.total_sales_value}")

print("\n[DONE]")
