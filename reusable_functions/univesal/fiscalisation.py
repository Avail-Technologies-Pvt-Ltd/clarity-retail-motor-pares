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

    fiscal_receipts = FiscalReceipt.objects.filter(local_receipt_number=local_invoice_number)
    if fiscal_receipts:
        fiscal_receipt = fiscal_receipts.first()
        fiscal_details = {
            "is_fiscalised": True,
            "url": fiscal_receipt.qr_code_url,
            "fiscal_day": "",
            "global_count": fiscal_receipt.inv_number_global,
            "fiscal_count": "",
            "validation_code": ""
        }

    return fiscal_details




def is_correct_hs_code_format(s):
    return len(s) == 8 and s.isdigit()