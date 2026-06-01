"""
Register a new ZIMRA test device, fetch its certificate, and save it
alongside the generated private key.

Reads from inline constants below — keep them in sync with the device
spreadsheet ZIMRA emails you.

Output:
  fiscalisation/certs/certificate.crt
  fiscalisation/certs/decrypted_key.key
"""

import os
import sys
import logging

# Make local fiscalisation/services.py importable without Django setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fiscalisation.services import register_new_device

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ---- Device details from dev1.xlsx (proper VAT device) ----
SERIAL_NO = 'testserial2'
DEVICE_ID = '35454'
ACTIVATION_KEY = '00832487'  # zero-padded to 8 digits
MODEL_NAME = 'Server'
USE_PROD = False  # Test environment

CERT_DIR = 'fiscalisation/certs'
CERT_FILENAME = 'certificate'  # -> certificate.crt
KEY_FILENAME = 'decrypted_key'  # -> decrypted_key.key

os.makedirs(CERT_DIR, exist_ok=True)

register_new_device(
    fiscal_device_serial_no=SERIAL_NO,
    device_id=DEVICE_ID,
    activation_key=ACTIVATION_KEY,
    model_name=MODEL_NAME,
    folder_name=CERT_DIR,
    certificate_filename=CERT_FILENAME,
    private_key_filename=KEY_FILENAME,
    prod=USE_PROD,
)

print()
print(f"Cert: {CERT_DIR}/{CERT_FILENAME}.crt")
print(f"Key:  {CERT_DIR}/{KEY_FILENAME}.key")
