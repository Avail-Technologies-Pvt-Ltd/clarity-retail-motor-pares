from fiscalisation.models import *


def get_fiscal_details(document_type, local_document_id):
    if document_type == "RECEIPT":
        document_type = "FISCALINVOICE"
        print(document_type)
        print(document_type)
        print(document_type)
        print(document_type)
        fiscal_details = {
            "is_fiscalised": False,
            "url": "uuu",
            "fiscal_day": "",
            "global_count": "",
            "fiscal_count": "",
            "validation_code": ""
        }

        local_receipt_number = local_document_id
        fiscal_receipts = FiscalReceipt.objects.filter(local_receipt_number=local_receipt_number)
        print(local_document_id)
        print(fiscal_receipts)
        print("----------------------------------")
        fiscal_receipts = FiscalReceipt.objects.filter(doc_type=document_type, local_receipt_number=local_receipt_number)
        print(fiscal_receipts)
        if fiscal_receipts:
            fiscal_receipt = fiscal_receipts.last()
            print(fiscal_receipt.id)
            print(fiscal_receipt.id)
            print(fiscal_receipt.id)
            print(fiscal_receipt.qr_code_url)
            print(fiscal_receipt.id)
            print(fiscal_receipt.id)
            print(fiscal_receipt.id)
            print(fiscal_receipt.id)
            fiscal_details = {
                "is_fiscalised": True,
                "url": fiscal_receipt.qr_code_url,
                "fiscal_day": "",
                "global_count": fiscal_receipt.inv_number_global,
                "fiscal_count": "",
                "validation_code": ""
            }
        
        print("=================================================================|||||||||||||||||||||||||||||||")
        print(fiscal_details)
        print("=================================================================|||||||||||||||||||||||||||||||")

        return fiscal_details


    elif document_type == "CREDITNOTE":
        print(document_type)
        print(document_type)
        print(document_type)
        print(document_type)
        fiscal_details = {
            "is_fiscalised": False,
            "url": "",
            "fiscal_day": "",
            "global_count": "",
            "fiscal_count": "",
            "validation_code": ""
        }


        local_credit_note_number = local_document_id
        fiscal_receipts = FiscalReceipt.objects.filter(local_invoice_number_to_credit_debit=local_credit_note_number)
        print(local_document_id)
        print(fiscal_receipts)
        print("----------------------------------")
        fiscal_receipts = FiscalReceipt.objects.filter(doc_type=document_type, local_invoice_number_to_credit_debit=local_credit_note_number)
        print(fiscal_receipts)
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

        print("=================================================================|||||||||||||||||||||||||||||||")
        print(fiscal_details)
        print("=================================================================|||||||||||||||||||||||||||||||")

        return fiscal_details

    return 0


def is_correct_hs_code_format(s):
    return len(s) == 8 and s.isdigit()