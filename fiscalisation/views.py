# fiscalisation/views.py

from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .services import Device


# INITIALIZE DEVICE

device = Device(
    device_id="35440",
    serialNo="572",
    activationKey="00335051",

    cert_path="fiscalisation/certs/certificate.crt",
    private_key_path="fiscalisation/certs/decrypted_key.key",

    test_mode=True,

    deviceModelName="Server",
    deviceModelVersion="v1",

    company_name="AVAIL TECHNOLOGIES"
)






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
# GET STATUS
# -----------------------------------------

def get_status(request):

    try:

        response = device.getStatus()

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
# OPEN FISCAL DAY
# -----------------------------------------

@csrf_exempt
def open_day(request):

    try:

        response = device.openDay(
            fiscalDayNo=1
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


# -----------------------------------------
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

            "receiptDate": datetime.now().strftime(
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