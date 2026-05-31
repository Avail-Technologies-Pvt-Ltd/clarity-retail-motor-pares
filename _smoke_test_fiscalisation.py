"""
Smoke test for the fiscalization wiring.
Tests:
  1. All modules import cleanly
  2. URLs resolve
  3. build_fiscal_day_counters aggregates correctly
  4. dashboard_data endpoint returns 200 with empty state
  5. open_day / close_day return JSON when device is misconfigured
This does NOT call ZIMRA.
"""

import os
import sys
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'point_of_sale.settings_dev'
django.setup()

from decimal import Decimal
from django.urls import reverse, resolve
from django.test import Client


def t(label):
    print(f"\n[TEST] {label}")


def ok(msg):
    print(f"  OK  {msg}")


def fail(msg):
    print(f"  FAIL {msg}")
    sys.exit(1)


# ---------------------------------------------------------------------
# 1. Imports
# ---------------------------------------------------------------------
t("Imports")
try:
    from fiscalisation import views as fv
    from fiscalisation.models import FiscalDevice, FiscalState, FiscalReceipt, FiscalDaySummary
    from pos import views as pv
    from payments.models import VATCode, PaymentMethod
    ok("fiscalisation, pos, payments modules imported")
except Exception as e:
    fail(f"import error: {e}")

# Verify the new fields exist on the models
try:
    assert any(f.name == 'zimra_tax_id' for f in VATCode._meta.get_fields()), "VATCode.zimra_tax_id missing"
    assert any(f.name == 'zimra_money_type_code' for f in PaymentMethod._meta.get_fields()), "PaymentMethod.zimra_money_type_code missing"
    ok("zimra_tax_id and zimra_money_type_code present on models")
except AssertionError as e:
    fail(str(e))

# Verify `device` import on pos.views worked
if hasattr(pv, 'device'):
    ok("pos.views.device imported")
else:
    fail("pos.views.device not present")

# ---------------------------------------------------------------------
# 2. URL resolution
# ---------------------------------------------------------------------
t("URL resolution")
for path, expected_view in [
    ('/fiscalisation/dashboard/', 'dashboard'),
    ('/fiscalisation/api/dashboard-data/', 'dashboard_data'),
    ('/fiscalisation/api/open-day/', 'open_day'),
    ('/fiscalisation/api/close-day/', 'close_day'),
    ('/fiscalisation/api/create-test-receipt/', 'test_receipt'),
    ('/fiscalisation/open-day/', 'open_day'),
    ('/fiscalisation/close-day/', 'close_day'),
    ('/fiscalisation/status/', 'get_status'),
]:
    try:
        match = resolve(path)
        if match.func.__name__ == expected_view:
            ok(f"{path} -> {expected_view}")
        else:
            fail(f"{path} resolved to {match.func.__name__}, expected {expected_view}")
    except Exception as e:
        fail(f"{path} failed to resolve: {e}")

# ---------------------------------------------------------------------
# 3. build_fiscal_day_counters aggregation
# ---------------------------------------------------------------------
t("build_fiscal_day_counters aggregation")

from accounts.models import User, Branch
from datetime import date

# Create a minimal test user (or fetch one)
user, _ = User.objects.get_or_create(
    username='__smoke_test__',
    defaults={'is_active': True}
)

# Create FiscalDevice + FiscalState
device_row, _ = FiscalDevice.objects.get_or_create(
    device_id='35420',
    defaults={
        'serial_no': 'availtech-1',
        'activation_key': '00338713',
        'company_name': 'AVAIL TECHNOLOGIES',
        'is_test_mode': True,
        'is_active': True,
    }
)
state, _ = FiscalState.objects.get_or_create(device=device_row)
state.fiscal_day_no = 99  # use a high day so we don't collide with anything
state.is_day_open = True
state.receipt_counter = 0
state.receipt_global_no = 0
state.current_day_date = date.today()
state.save()

# Clear any prior fixture receipts for this day
FiscalReceipt.objects.filter(fiscal_state=state, fiscal_day_no=99).delete()
FiscalDaySummary.objects.filter(fiscal_state=state, fiscal_day_no=99).delete()

# Build two fake FiscalReceipt rows representing one SaleByTax @ 15.5% with cash payment,
# and one CreditNote @ 15.5%.
sample_invoice_payload = {
    'receiptCurrency': 'USD',
    'receiptTaxes': [
        {'taxID': 515, 'taxPercent': 15.5, 'taxAmount': 12.07, 'salesAmountWithTax': 90.00},
    ],
    'receiptPayments': [
        {'moneyTypeCode': 0, 'paymentAmount': 90.00},
    ],
}
sample_credit_payload = {
    'receiptCurrency': 'USD',
    'receiptTaxes': [
        {'taxID': 515, 'taxPercent': 15.5, 'taxAmount': 2.01, 'salesAmountWithTax': 15.00},
    ],
    'receiptPayments': [
        {'moneyTypeCode': 0, 'paymentAmount': 15.00},
    ],
}

FiscalReceipt.objects.create(
    fiscal_state=state, fiscal_day_no=99, receipt_global_no=1, receipt_counter=1,
    receipt_type='FISCALINVOICE', invoice_no='SMOKE-INV-1', total_amount=Decimal('90.00'),
    local_hash='h1', local_signature='s1', qr_code_string='qr1',
    prepared_payload=sample_invoice_payload, sync_status='PENDING',
)
FiscalReceipt.objects.create(
    fiscal_state=state, fiscal_day_no=99, receipt_global_no=2, receipt_counter=2,
    receipt_type='CREDITNOTE', invoice_no='SMOKE-CN-1', total_amount=Decimal('15.00'),
    local_hash='h2', local_signature='s2', qr_code_string='qr2',
    prepared_payload=sample_credit_payload, sync_status='PENDING',
)
state.receipt_counter = 2
state.save()

counters = fv.build_fiscal_day_counters(state)
print(f"    counters: {counters}")

types = {c['fiscalCounterType'] for c in counters}
for required in {'SaleByTax', 'SaleTaxByTax', 'CreditNoteByTax', 'CreditNoteTaxByTax', 'BalanceByMoneyType'}:
    if required not in types:
        fail(f"missing counter type {required}")
ok("all 5 expected counter types present (SaleByTax, SaleTaxByTax, CreditNoteByTax, CreditNoteTaxByTax, BalanceByMoneyType)")

# Validate values
sale_by_tax = next(c for c in counters if c['fiscalCounterType'] == 'SaleByTax')
assert sale_by_tax['fiscalCounterValue'] == 90.00, f"SaleByTax wrong: {sale_by_tax}"
assert sale_by_tax['fiscalCounterTaxID'] == 515
assert sale_by_tax['fiscalCounterTaxPercent'] == 15.5
ok(f"SaleByTax = 90.00 @ 15.5% (taxID 515)")

balance = next(c for c in counters if c['fiscalCounterType'] == 'BalanceByMoneyType')
# Cash: +90 - 15 = 75
assert balance['fiscalCounterValue'] == 75.00, f"BalanceByMoneyType wrong: {balance}"
assert balance['fiscalCounterMoneyType'] == 0
ok(f"BalanceByMoneyType cash = 75.00 (90 invoice − 15 credit note)")

# ---------------------------------------------------------------------
# 4. dashboard_data endpoint
# ---------------------------------------------------------------------
t("dashboard_data endpoint")
client = Client(HTTP_HOST='localhost')
resp = client.get('/fiscalisation/api/dashboard-data/')
print(f"    status={resp.status_code}")
print(f"    body  ={resp.json()}")
if resp.status_code == 200 and resp.json().get('success') is True:
    ok("/api/dashboard-data/ returned success")
else:
    fail(f"dashboard_data returned {resp.status_code} {resp.json()}")

# ---------------------------------------------------------------------
# 5. open_day / close_day with no certs - expect graceful failure
# ---------------------------------------------------------------------
t("open_day handles missing certs gracefully")
resp = client.get('/fiscalisation/api/open-day/')
data = resp.json()
print(f"    status={resp.status_code} body={data}")
# Day is open in DB, so we should get the "already open" error -- but real test
# wants the JSON shape to be valid
if 'success' in data:
    ok("open_day returned JSON with success key")
else:
    fail(f"open_day returned malformed response: {data}")

# Close day will attempt to call ZIMRA closeDay but cert load will fail
t("close_day with no certs")
resp = client.get('/fiscalisation/api/close-day/')
data = resp.json()
print(f"    status={resp.status_code} body={data}")
if 'success' in data:
    ok("close_day returned JSON with success key")
else:
    fail(f"close_day returned malformed response: {data}")

# Cleanup
FiscalReceipt.objects.filter(fiscal_state=state, fiscal_day_no=99).delete()
FiscalDaySummary.objects.filter(fiscal_state=state, fiscal_day_no=99).delete()

print("\n[DONE] All smoke tests passed.")
