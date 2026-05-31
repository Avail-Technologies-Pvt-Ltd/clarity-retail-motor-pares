# Clarity Retail POS — with ZIMRA FDMS Fiscalisation

Django-based point-of-sale system with integrated ZIMRA fiscalisation (open
day, sign + submit receipts, close day) for Zimbabwean tax compliance.

End-to-end validated against the ZIMRA test environment:
`https://fdmsapitest.zimra.co.zw`.

---

## Quick start (dev, ~5 minutes)

```bash
# 1. Clone
git clone <repo-url>
cd CLARITY-RETAIL-LIVE-FISCAL

# 2. Virtualenv
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate

# 3. Install
pip install -r requirements.txt

# 4. Migrate (SQLite for dev, no DB to configure)
python manage.py migrate --settings=point_of_sale.settings_dev

# 5. Run
python manage.py runserver --settings=point_of_sale.settings_dev
```

Open `http://localhost:8000/fiscalisation/devices/` — you're in.

---

## First-time device setup (no CLI required)

The system is designed so a reseller can add a new ZIMRA device through the
web UI, without touching code or `.env` files.

1. **Browse to** `/fiscalisation/devices/` → click **+ Add Device**
2. **Fill the form** with the credentials ZIMRA emailed when the device was
   issued:
   - `device_id` (e.g. `35454`)
   - `serial_no` (e.g. `testserial2`)
   - `activation_key` — pad to 8 digits (e.g. `82671` → `00082671`)
   - `company_name`
   - `is_test_mode` — check for ZIMRA test, uncheck for production
3. **Install the cert** — pick ONE option on the device detail page:
   - **Generate CSR + Fetch Cert** — generates a fresh RSA-2048 keypair,
     sends the CSR to ZIMRA, saves the issued certificate. Requires
     internet + a valid activation key.
   - **Upload existing cert + key** — for a device already registered
     elsewhere; upload the matching `.crt` and `.key` PEM files.
4. **Click Test connection** to confirm `ping` + `getStatus` + `getConfig`
   all return clean.
5. **Click Set as Active Device** — the running app immediately starts using
   this device for receipts. No restart needed.

To switch a device between test and production, edit the device and toggle
`is_test_mode`. The cert files must come from the matching environment.

---

## Running in production

```bash
python run.py
```

This uses waitress on port `8081`, single-process / multi-threaded. The
background scheduler boots automatically and runs:

- `sync_pending_receipts` every 2 minutes — pushes any FiscalReceipts that
  were signed locally during an internet outage up to ZIMRA when reachable.
- `reconcile_with_zimra` daily at 04:00 CAT — keeps local FiscalState in
  sync with ZIMRA, including after a manual close on ZIMRA's portal.
- `prune_apscheduler_history` Sundays at 03:00 CAT — keeps the scheduler
  log table from growing forever.

No cron job, no separate worker daemon, nothing for the operator to manage.

---

## Operational features

- **Pre-flight receipt validator** rejects bad receipts at the till
  (totals mismatch, invalid tax_percent, wrong moneyTypeCode, wrong sign
  for the receipt type) before they reach ZIMRA.
- **Day-age banner** on the dashboard warns when a fiscal day is
  approaching ZIMRA's `taxPayerDayMaxHrs` cap (default 24h).
- **Cert-expiry badge** in the device list flags certs nearing expiry;
  the system refuses to open a new fiscal day when <7 days remain.
- **Concurrency lock** on `FiscalState` so two simultaneous checkouts
  can't race on `receipt_global_no`.
- **HTTP timeouts** (30s) on every ZIMRA call — a misbehaving server
  cannot hang a cashier.
- **Close-day gating** — refuses to call closeDay if any local FiscalReceipt
  is still `PENDING` or `FAILED` for that day; surfaces the blocking list.
- **Reconcile + Sync Pending buttons** on the dashboard for one-click
  manual recovery.

---

## Environment configuration

For dev, just use `settings_dev` (SQLite, no config). For production, copy
`.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

The `.env` only seeds the first FiscalDevice row on first boot if the DB is
empty — after that, the UI is authoritative. You can ignore `.env` entirely
and add the first device through the UI.

For production database (Postgres), set the standard `DB_*` env vars (see
`.env.example`).

---

## Troubleshooting

**`Day will not close: ReceiptsWithValidationErrors`** — A receipt in the
day was rejected by ZIMRA. Email ZIMRA to manually close the day, then
hit **Reconcile with ZIMRA** on the dashboard to sync local state.

**`RCPT020` (Invoice signature not valid) or `RCPT014` (Receipt date earlier
than fiscal day open)** — Usually clock-related. Ensure the host machine's
clock is set to Zimbabwe time (CAT, UTC+2). The system internally uses
CAT regardless of system clock, but a wildly wrong host clock can still
trip ZIMRA's other checks.

**`No active FiscalDevice configured`** — Visit `/fiscalisation/devices/`
and either add+activate one, or set an existing device to active.

**Disable the background scheduler temporarily:**
```bash
DISABLE_SCHEDULER=1 python run.py
```

---

## Architecture

- `pos/` — cart, checkout, prints
- `payments/` — `SaleTransaction`, `Sale`, `Payment`, `VATCode`, `PaymentMethod`
- `enventory/` — products, stock, batches
- `fiscalisation/` — everything ZIMRA:
  - `services.py` — `Device` class (CSR/registration, sign, submit, openDay,
    closeDay, QR code), `validate_receipt_for_zimra`, `zimra_now`
  - `views.py` — dashboard, device management UI, fiscal endpoints,
    `reconcile_with_zimra`, `classify_submit_response`
  - `models.py` — `FiscalDevice`, `FiscalState`, `FiscalReceipt`,
    `FiscalDaySummary`
  - `scheduler.py` — APScheduler jobs (started by `apps.py`)
  - `management/commands/sync_pending_receipts.py` — manual/cron entry
    point for the sync worker

Receipt flow on checkout (see `pos/views.py:check_out`):

1. Lock `FiscalState` (select_for_update) — serialise the counter
2. Build receipt payload from cart
3. Pre-flight validate (`validate_receipt_for_zimra`)
4. Sign locally (`device.prepareReceipt`)
5. Try `device.submitReceipt` — classify response (`SUCCESS` /
   `FAILED` / `PENDING`)
6. Persist `FiscalReceipt` with the classified status, update `FiscalState`
7. Print
8. Return to cashier

If step 5 fails (network/timeout), the receipt is `PENDING` and the
background scheduler picks it up within 2 minutes.
