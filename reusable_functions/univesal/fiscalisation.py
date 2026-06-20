from fiscalisation.models import *

def get_fiscal_details(local_invoice_number):
    fiscal_details = {
        "is_fiscalised": False,
        "url": "",
        "fiscal_day": "",
        "global_count": "",
        "fiscal_count": "",
        "validation_code": ""
    }

    fiscal_receipts = FiscalReceipt.objects.filter(internal_invoice_id=local_invoice_number)
    if fiscal_receipts:
        fiscal_receipt = fiscal_receipts.first()
        fiscal_details = {
            "is_fiscalised": True,
            "url": fiscal_receipt.qr_code_url,
            "fiscal_day": "",
            "global_count": fiscal_receipt.fiscal_receipt_global_no,
            "fiscal_count": "",
            "validation_code": ""
        }

    return fiscal_details