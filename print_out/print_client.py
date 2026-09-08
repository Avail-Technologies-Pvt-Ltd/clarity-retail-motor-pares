import json
import logging
import socket

from decimal import Decimal


from reusable_functions.univesal.client_spacific_functions.client_spacific_functions import custome_wraper
from reusable_functions.univesal.fiscalisation import get_fiscal_details

from django.http import HttpResponseRedirect

from .models import Printer

from accounts.models import ClientSetting, Branch
from payments.models import SaleTransaction, Payment, Sale, PaymentMethod
from enventory.models import CreditNote, ReturnInn
from pos.models import Quotation, QuotationItem


from datetime import datetime


import locale

try:
    configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
except Exception as e:
    HttpResponseRedirect('client_settings_page')

locale.setlocale(locale.LC_ALL, '') 

logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT = 10


# ============================================================
# PRINTER PICKER
# ============================================================

def get_printer(request):
    from .views import printer_health
    # 1. Try to get the user's assigned printer
    try:
        printer = request.user.current_printer
        if printer and printer.enabled:
            # Call your existing view function directly
            health_response = printer_health(request, printer_id=printer.id)
            health_data = json.loads(health_response.content)
            
            if health_data.get("online") is True:
                return printer
    except Exception:
        pass

    # 2. Fallback: Loop through enabled default printers
    default_printers = Printer.objects.filter(enabled=True, is_default=True)
    for printer in default_printers:
        health_response = printer_health(request, printer_id=printer.id)
        health_data = json.loads(health_response.content)
        
        if health_data.get("online") is True:
            return printer

    # 3. Final Fallback: Loop through all enabled printers
    all_enabled_printers = Printer.objects.filter(enabled=True)
    for printer in all_enabled_printers:
        health_response = printer_health(request, printer_id=printer.id)
        health_data = json.loads(health_response.content)
        
        if health_data.get("online") is True:
            return printer

    # Ultimate safety net if no printers are enabled and online
    return None




# ============================================================
# SEND TO WINDOWS PRINT SERVER
# ============================================================

def send_to_print_server(server_ip, server_port, printer_name, print_type="text", text="", text1="", text2="", qr_data="", footer="", logo_data=None, document=None, timeout=DEFAULT_TIMEOUT):
    """
    Send a print request to the Windows Print Server.
    """
    
    # server_ip is already resolved by the model's get_resolved_ip() method

    payload = {
        "type": print_type,
        "printer_name": printer_name,
    }

    # ----------------------------------------------------------
    # Legacy text printing
    # ----------------------------------------------------------

    if print_type == "text":

        payload["text"] = text

    # ----------------------------------------------------------
    # Legacy full receipt
    # ----------------------------------------------------------

    elif print_type == "full_receipt":

        payload.update({

            "text1": text1,

            "text2": text2,

            "qr_data": qr_data,

            "footer": footer,

            "logo_data": logo_data,

        })

    # ----------------------------------------------------------
    # Legacy QR printing
    # ----------------------------------------------------------

    elif print_type == "qr_only":

        payload["qr_data"] = qr_data

    # ----------------------------------------------------------
    # NEW GENERIC DOCUMENT
    # ----------------------------------------------------------

    elif print_type == "document":

        if not isinstance(
            document,
            dict,
        ):

            return {

                "status": "error",

                "message": (
                    "Document must be a dictionary."
                ),

            }

        payload["document"] = document

    else:

        return {

            "status": "error",

            "message": (
                f"Unsupported print type: {print_type}"
            ),

        }

    # ========================================================
    # SEND
    # ========================================================

    try:

        logger.info(
            "Connecting to print server %s:%s",
            server_ip,
            server_port,
        )

        with socket.create_connection(

            (
                server_ip,
                server_port,
            ),

            timeout=timeout,

        ) as sock:

            data = json.dumps(
                payload,
                ensure_ascii=False,
            ).encode("utf-8")

            logger.info(
                "Sending %s bytes",
                len(data),
            )

            sock.sendall(
                data
            )

            # --------------------------------------------------
            # Tell server that no more request data is coming.
            # This is useful for clean TCP handling.
            # --------------------------------------------------

            try:

                sock.shutdown(
                    socket.SHUT_WR
                )

            except OSError:

                pass

            response = sock.recv(
                4096
            )

        # ====================================================
        # RESPONSE
        # ====================================================

        if not response:

            return {

                "status": "error",

                "message": (
                    "Print server returned no response."
                ),

            }

        try:

            result = json.loads(
                response.decode(
                    "utf-8"
                )
            )

        except json.JSONDecodeError:

            logger.error(
                "Invalid JSON response: %s",
                response[:500],
            )

            return {

                "status": "error",

                "message": (
                    "Invalid response from print server."
                ),

            }

        return result

    except socket.timeout:

        return {

            "status": "error",

            "message": (
                "Connection timed out connecting to "
                f"{server_ip}:{server_port}."
            ),

        }

    except ConnectionRefusedError:

        return {

            "status": "error",

            "message": (
                f"Connection refused by "
                f"{server_ip}:{server_port}. "
                "Make sure the Windows Print Server "
                "is running."
            ),

        }

    except OSError as e:

        return {

            "status": "error",

            "message": str(e),

        }

    except Exception as e:

        logger.exception(
            "Unexpected print error"
        )

        return {

            "status": "error",

            "message": str(e),

        }


# ============================================================
# TEST PRINTER
# ============================================================

def test_printer(
    printer,
    logo_data=None,
):
    """
    Existing printer test.

    This now uses the generic document architecture.
    """

    document = {
        "type": "document",

        "printer_name": printer.name,

        "paper": {
            "width": 80,
            "cut": True,
            "copies": 1,
        },

        "content": [

            {
                "type": "image",
                "data": logo_data,
                "align": "center",
                "width": 350,
            },

            {
                "type": "text",
                "text": "CLARITY RETAIL",
                "align": "center",
                "bold": True,
                "size": 2,
            },

            {
                "type": "text",
                "text": "PRINT TEST RECEIPT",
                "align": "center",
                "bold": True,
            },

            {
                "type": "divider",
            },

            {
                "type": "text",
                "text": "Normal text test",
                "align": "left",
            },

            {
                "type": "text",
                "text": "Centered text test",
                "align": "center",
            },

            {
                "type": "text",
                "text": "Right aligned text test",
                "align": "right",
            },

            {
                "type": "divider",
            },

            {
                "type": "row",
                "columns": [
                    {
                        "text": "Item",
                        "align": "left",
                        "bold": True,
                    },
                    {
                        "text": "Qty",
                        "align": "center",
                        "bold": True,
                    },
                    {
                        "text": "Amount",
                        "align": "right",
                        "bold": True,
                    },
                ],
            },

            {
                "type": "row",
                "columns": [
                    {
                        "text": "Test Product",
                        "align": "left",
                    },
                    {
                        "text": "2",
                        "align": "center",
                    },
                    {
                        "text": "10.00",
                        "align": "right",
                    },
                ],
            },

            {
                "type": "row",
                "columns": [
                    {
                        "text": "Another Item",
                        "align": "left",
                    },
                    {
                        "text": "1",
                        "align": "center",
                    },
                    {
                        "text": "25.00",
                        "align": "right",
                    },
                ],
            },

            {
                "type": "divider",
            },

            {
                "type": "text",
                "text": "TOTAL: 35.00",
                "align": "right",
                "bold": True,
                "size": 2,
            },

            {
                "type": "divider",
            },

            {
                "type": "text",
                "text": "QR CODE TEST",
                "align": "center",
                "bold": True,
            },

            {
                "type": "qr",
                "data": "https://avail.co.zw",
                "align": "center",
                "size": 6,
            },

            {
                "type": "text",
                "text": "Scan this QR code",
                "align": "center",
            },

            {
                "type": "divider",
            },

            {
                "type": "text",
                "text": "Printer: " + printer.name,
                "align": "center",
            },

            {
                "type": "text",
                "text": "Windows Print Server",
                "align": "center",
            },

            {
                "type": "text",
                "text": "PRINT TEST SUCCESSFUL",
                "align": "center",
                "bold": True,
            },

        ],
    }

    return print_document(
        printer,
        document,
    )




# ============================================================
# ACTUAL PRINTING
# ============================================================

def print_this_document(request, printer, document_type, document_id, is_copy):
    logo_data = configuration.logo_base64
    print("---------------------------")
    print("---------------------------")
    print(document_type)
    print("---------------------------")


    if document_type == "CREDITNOTE":
        print(document_type)
        fiscal_details = get_fiscal_details("CREDITNOTE", document_id) #documnebt id is the local document id
        credit_note = CreditNote.objects.get(id=int(document_id))

        if credit_note:
            # variable diclaration---------------------------------
            sale_transaction = credit_note.sale_transaction
            receipt_money_portions = Payment.objects.filter(payment_for="RECEIPT", payment_for_id=int(sale_transaction.recipt_number))
            refund_money_portions = Payment.objects.filter(payment_for="CREDIT_NOTE", payment_for_id=credit_note.id)

            dominant_money_portion = receipt_money_portions[0]
            dominant_money_portion_rate = dominant_money_portion.rate
            dominant_money_portion_shortcut = dominant_money_portion.payment_method.shortcut

            discount = sale_transaction.discount
            # -----------------------------------------

            document = {
                'type': "document",
                'printer_name': printer.name,
                'paper': {
                    'width': 80, #add printer.width
                    'cut': True,
                    'copies': 1,
                },

                'content': [
                    {
                        "type": "text",
                        "text": f"""------------------------------------------------
CREDIT NOTE
------------------------------------------------
{ is_copy }

""",
                        "align": "center",
                    },

                    {
                        'type': "image",
                        'data': logo_data,
                        'align': "center",
                        'width': 350,
                    },

                    {
                        'type': "text",
                        'text': configuration.company_name.upper(),
                        'align': "center",
                        'bold': True,
                        'size': 1,
                    },

                    {
                        "type": "divider",
                    },


                    {
                        "type": "text",
                        "text": f"""{custome_wraper(configuration.address)}
{custome_wraper(configuration.tel)}
Email        : {configuration.email}
------------------------------------------------
VAT          : {configuration.vat_number}
TIN          : {configuration.tin_number}
PRZ          : {configuration.prz_number}
INVOICE #    : {credit_note.sale_transaction.ultimate_recipt_number}
CREDIT NOTE #: {credit_note.ultimate_credit_note_number}
------------------------------------------------
                    BUYER
Buyer Name   : {credit_note.sale_transaction.buyer_name}
Buyer TIN    : {credit_note.sale_transaction.buyer_tin}
Buyer VAT    : {credit_note.sale_transaction.buyer_vat}
Buyer Address: {custome_wraper(credit_note.sale_transaction.buyer_address)}
------------------------------------------------
Date     : {str(credit_note.created_at)[:16]}
Sales Rep: {credit_note.created_by.first_name.title()} {credit_note.created_by.last_name.title()}
------------------------------------------------
""",
                        "align": "left",
                    },

                    {
                        'type': "text",
                        'text': "BOUGHT",
                        'align': "center"
                    },

                    {
                        'type': "row",
                        'columns': [
                            {
                                'text': "Qty   Description",
                                'align': "left",
                                'bold': True,
                            },
                            {
                                'text': "Total Price",
                                'align': "right",
                                'bold': True,
                            },
                        ],
                    },

                    {
                        "type": "text",
                        "text": "------------------------------------------------",
                        "align": "left",
                    },
                ]
            }

            subtotal = 0
            VAT = 0
            bought_products_data = ""
            returned_products_data = ""

            sales = Sale.objects.filter(sale_transaction=sale_transaction)
            for sale in sales:
                subtotal += sale.quantity * sale.unit_price
                VAT += (sale.stock.product.vat_code.percentage/100) * (sale.quantity * sale.unit_price)

                document['content'].append({
                    'type': "row",
                    'columns': [
                        {
                            'text': f"{sale.quantity}  x  ({str(sale.stock.product.product_code)}) {str(sale.stock.product.title)}",
                            'align': "left",
                        },
                        {
                            "text": f"{ locale.format_string('%.2f', sale.selling_price * dominant_money_portion_rate, grouping=True) }",
                            "align": "right",
                        },

                    ]
                })


            returns_inn = ReturnInn.objects.filter(credit_note=credit_note)
            print(returns_inn)

            document['content'].append({
                'type': "text",
                'text': "------------------------------------------------",
                'align': "center"
            },)

            document['content'].append({
                'type': "text",
                'text': "RETURNED",
                'align': "center"
            },)

            document['content'].append({
                'type': "row",
                'columns': [
                    {
                        'text': "Qty   Description",
                        'align': "left",
                        'bold': True,
                    },
                    {
                        'text': "Total Price",
                        'align': "right",
                        'bold': True,
                    },
                ],
            },)

            for return_inn in returns_inn:
                document['content'].append({
                    'type': "row",
                    'columns': [
                        {
                            'text': f"{return_inn.total_units}  x  ({str(return_inn.sale.stock.product.product_code)}) {str(return_inn.sale.stock.product.title)}",
                            'align': "left",
                        },
                        {
                            "text": f"{ locale.format_string('%.2f', return_inn.total_units * return_inn.sale.unit_price * dominant_money_portion_rate, grouping=True) }",
                            "align": "right",
                        },
                    ]
                })

            document['content'].append({
                'type': "text",
                'text': "------------------------------------------------",
                'align': "center"
            },)

            document['content'].append({
                'type': "text",
                'text': "RETURN REASON",
                'align': "center"
            },)

            document['content'].append({
                'type': "text",
                'text': f"""{ credit_note.reason.details}
{ credit_note.notes}""",
                'align': "left",
            },)
                
            total_cost = (VAT + subtotal) - discount

            

            suma = f"""
------------------------------------------------
{dominant_money_portion_shortcut} transaction.
{'Subtotal':<10}{ locale.format_string('%.2f', subtotal * dominant_money_portion_rate, grouping=True):>20}
{'Discount':<10}{ locale.format_string('%.2f', discount * dominant_money_portion_rate, grouping=True):>20}
{'VAT     ':<10}{ locale.format_string('%.2f', VAT * dominant_money_portion_rate, grouping=True):>20}
------------------------------------------------
{'Total   ':<10}{ locale.format_string('%.2f', total_cost * dominant_money_portion_rate, grouping=True):>20}
```````````````````````````````````````````````` """
            document['content'].append({
                    'type': "text",
                    'text': suma,
                    'align': "left",
               })


            document['content'].append({
                'type': "text",
                'text': f"""PAID:""",
                'align': 'left',
                'bold': True
            })
            portions = Payment.objects.filter(payment_for="RECEIPT", payment_for_id=sale_transaction.recipt_number)
            for portion in portions:
                document['content'].append({
                    'type': "row",
                    'columns': [
                        {
                            'text': " ",
                            'align': "left"
                        },
                        {
                            'text': f"{ portion.payment_method.shortcut }",
                            'align': "center"
                        },
                        {
                            'text': f"{ locale.format_string('%.2f', portion.amount_paid, grouping=True) }",
                            'align': 'right'
                        }
                    ]
                })


            document['content'].append({
                'type': "text",
                'text': f"""REFUNDED:""",
                'align': 'left',
                'bold': True
            })

            portions = Payment.objects.filter(payment_for="CREDIT_NOTE", payment_for_id=credit_note.id)
            for portion in portions:
                document['content'].append({
                    'type': "row",
                    'columns': [
                        {
                            'text': " ",
                            'align': "left"
                        },
                        {
                            'text': f"{ portion.payment_method.shortcut }",
                            'align': "center"
                        },
                        {
                            'text': f"{ locale.format_string('%.2f', portion.amount_paid, grouping=True) }",
                            'align': 'right'
                        }
                    ]
                })

            document['content'].append({
                    'type': "text",
                    'text': f"""

BUYER'S SIGNATURE

_______________________________

------------------------------------------------
                    """,
                    'align': "center"
                })


            document['content'].append({
                    'type': "text",
                    'text': f"{configuration.thank_you_message}",
                    'align': "center",
                    'bold': True,
                })

            # Build fiscal text
            if fiscal_details and fiscal_details.get('is_fiscalised') == True:
                document['content'].append({
                    'type': "text",
                    'text': f"""

------------------------------------------------
FISCAL QR CODE
                    """,
                    'align': 'center'   
                })

                document['content'].append({
                    'type': "qr",
                    'data': f"{fiscal_details.get('url', '')}",
                    'align': "center",
                    'size': 10,
                })

                document['content'].append({
                    'type': "text",
                    'text': f"""
Fiscal Day      : {fiscal_details.get('fiscal_day', '')}
Global Count    : {fiscal_details.get('global_count', '')}
Fiscal Count    : {fiscal_details.get('fiscal_count', '')}
Validation Code : {fiscal_details.get('validation_code', '')}""",
                    'align': "left",
                })
        

            else:
                document['content'].append({
                    'type': "text",
                    'text': f"""

------------------------------------------------
FISCAL QR CODE

NETWORK ERROR WITH FISCAL DATA

*** The QR Code is on the ERP Invoice""",
                    'align': "center",
                })


            document['content'].append({
                    'type': "text",
                    'text': f"""


                    """,
                    'align': "center"
                })

        return print_document(
            printer,
            document,
        )








    elif document_type == "RECEIPT":
        print(document_type)

        fiscal_details = get_fiscal_details("RECEIPT", document_id)
        receipt = SaleTransaction.objects.get(recipt_number=int(document_id))

        if receipt:
            document = {
                'type': "document",
                'printer_name': printer.name,
                'paper': {
                    'width': 80, #add printer.width
                    'cut': True,
                    'copies': 1,
                },

                'content': [
                    {
                        "type": "text",
                        "text": f"""------------------------------------------------
FISCAL TAX INVOICE
------------------------------------------------
{ is_copy }

""",
                        "align": "center",
                    },

                    {
                        'type': "image",
                        'data': logo_data,
                        'align': "center",
                        'width': 350,
                    },

                    {
                        'type': "text",
                        'text': configuration.company_name.upper(),
                        'align': "center",
                        'bold': True,
                        'size': 1,
                    },

                    {
                        "type": "divider",
                    },


                    {
                        "type": "text",
                        "text": f"""{custome_wraper(configuration.address)}
{custome_wraper(configuration.tel)}
Email    : {configuration.email}
------------------------------------------------
VAT      : {configuration.vat_number}
TIN      : {configuration.tin_number}
PRZ      : {configuration.prz_number}
INVOICE #: {receipt.ultimate_recipt_number}
------------------------------------------------
                    BUYER
Buyer Name   : {receipt.buyer_name}
Buyer TIN    : {receipt.buyer_tin}
Buyer VAT    : {receipt.buyer_vat}
Buyer Address: {custome_wraper(receipt.buyer_address)}
------------------------------------------------
Date     : {str(receipt.created_at)[:16]}
Sales Rep: {receipt.created_by.first_name.title()} {receipt.created_by.last_name.title()}
------------------------------------------------
""",
                        "align": "left",
                    },

                    {
                        'type': "row",
                        'columns': [
                            {
                                'text': "Qty   Description",
                                'align': "left",
                                'bold': True,
                            },
                            {
                                'text': "Total Price",
                                'align': "right",
                                'bold': True,
                            },
                        ],
                    },

                    {
                        "type": "text",
                        "text": f"""------------------------------------------------""",
                        "align": "left",
                    },

                ]
            }

            sales = Sale.objects.filter(sale_transaction=int(receipt.recipt_number))
            dominant_money_portion = Payment.objects.filter(payment_for="RECEIPT", payment_for_id=int(receipt.recipt_number))[0]
            dominant_money_portion_rate = dominant_money_portion.rate
            dominant_money_portion_shortcut = dominant_money_portion.payment_method.shortcut

            subtotal = 0
            VAT = 0
            total_cost = 0
            discount = receipt.discount

            for sale in sales:
                subtotal += sale.quantity * sale.unit_price
                VAT += (sale.stock.product.vat_code.percentage/100) * (sale.quantity * sale.unit_price)

                document['content'].append({
                    'type': "row",
                    'columns': [
                        {
                            "text": f"{sale.quantity}  x  ({str(sale.stock.product.product_code)}) {str(sale.stock.product.title)} ",
                            "align": "left",
                        },
                        {
                            "text": f"{ locale.format_string('%.2f', sale.selling_price * dominant_money_portion_rate, grouping=True) }",
                            "align": "right",
                        },
                    ],
                })

            total_cost = (VAT + subtotal) - discount

            suma = f"""

------------------------------------------------
{dominant_money_portion_shortcut} transaction.
{'Subtotal':<10}{ locale.format_string('%.2f', subtotal * dominant_money_portion_rate, grouping=True):>20}
{'Discount':<10}{ locale.format_string('%.2f', discount * dominant_money_portion_rate, grouping=True):>20}
{'VAT     ':<10}{ locale.format_string('%.2f', VAT * dominant_money_portion_rate, grouping=True):>20}
------------------------------------------------
{'Total   ':<10}{ locale.format_string('%.2f', total_cost * dominant_money_portion_rate, grouping=True):>20}
```````````````````````````````````````````````` """

            document['content'].append({
                    'type': "text",
                    'text': suma,
                    'align': "left",
               })

            document['content'].append({
                    'type': "text",
                    'text': f"{configuration.thank_you_message}",
                    'align': "center"
                })

            # Build fiscal text
            if fiscal_details and fiscal_details.get('is_fiscalised') == True:
                document['content'].append({
                    'type': "text",
                    'text': f"""

------------------------------------------------
FISCAL QR CODE
                    """,
                    'align': 'center'   
                })

                document['content'].append({
                    'type': "qr",
                    'data': f"{fiscal_details.get('url', '')}",
                    'align': "center",
                    'size': 10,
                })

                document['content'].append({
                    'type': "text",
                    'text': f"""
Fiscal Day      : {fiscal_details.get('fiscal_day', '')}
Global Count    : {fiscal_details.get('global_count', '')}
Fiscal Count    : {fiscal_details.get('fiscal_count', '')}
Validation Code : {fiscal_details.get('validation_code', '')}""",
                    'align': "left",
                })
        

            else:
                pass
#                 document['content'].append({
#                     'type': "text",
#                     'text': f"""

# ------------------------------------------------
# FISCAL QR CODE

# NETWORK ERROR WITH FISCAL DATA

# *** The QR Code is on the ERP Invoice""",
#                     'align': "center",
#                 })


            document['content'].append({
                    'type': "text",
                    'text': f"""


                    """,
                    'align': "center"
                })

        return print_document(
            printer,
            document,
        )

    elif document_type == "ORDERLIST":
        document = {
            "type": "document",

            "printer_name": printer.name,

            "paper": {
                "width": 80,
                "cut": True,
                "copies": 1,
            },

            "content": [
                {
                    "type": "text",
                    "text": f"""------------------------------------------------
ORDER LIST
------------------------------------------------
                    """,
                    "align": "center",
                },
                {
                    "type": "image",
                    "data": logo_data,
                    "align": "center",
                    "width": 350,
                },

                {
                    "type": "text",
                    "text": f"""{ configuration.company_name }""",
                    "align": "center",
                    "bold": True,
                    "size": 1,
                },

                {
                    "type": "text",
                    "text": f"""
------------------------------------------------
DATE: {datetime.strptime(str(datetime.today())[:10],"%Y-%m-%d").date()}
PREPARED BY: { request.user.first_name.title() } { request.user.first_name.title() }
------------------------------------------------
                    """,
                    "align": "center",
                },

                {
                    "type": "row",
                    "columns": [
                        {
                            "text": "PRODUCT",
                            "align": "left",
                            "bold": True,
                        },
                        {
                            "text": "[IN STOCK]",
                            "align": "center",
                            "bold": True,
                        },
                        {
                            "text": "BUY",
                            "align": "right",
                            "bold": True,
                        },
                    ],

                },

                {
                    "type": "text",
                    "text": f"""------------------------------------------------""",
                    "align": "center",
                },
            ]}

        order_list_array = request.GET.getlist('order_list_array')
        order_list_array = str(order_list_array)[2:-2]

        # Parse the JSON string into a Python list of dictionaries
        data = json.loads(order_list_array)

        for item in data:
            document['content'].append({
                "type": "row",
                    "columns": [
                        {
                            "text": f"{str(item['productDescription'])[:34]}",
                            "align": "left",
                        },
                        {
                            "text": f"[{item['totalUnitsAvailable']}] ",
                            "align": "center",
                        },
                        {
                            "text": f"{item['orderQuantity']}",
                            "align": "right",
                        },
                    ],
                })

        document['content'].append({
            "type": "text",
            "text": f"""------------------------------------------------



***STAMP***



------------------------------------------------
""",
            "align": "center",
        })

        return print_document(
            printer,
            document,
        )

    elif document_type == "QUOTATION":
        print(document_type)

        quotation = Quotation.objects.get(id=int(document_id))
        branch = Branch.objects.filter(is_local=True).first()
        customer = quotation.customer

        if quotation:
            document = {
                'type': "document",
                'printer_name': printer.name,
                'paper': {
                    'width': 80, #add printer.width
                    'cut': True,
                    'copies': 1,
                },

                'content': [
                    {
                        "type": "text",
                        "text": f"""------------------------------------------------
QUOTATION
------------------------------------------------
{ is_copy }

""",
                        "align": "center",
                    },

                    {
                        'type': "image",
                        'data': logo_data,
                        'align': "center",
                        'width': 350,
                    },

                    {
                        'type': "text",
                        'text': configuration.company_name.upper(),
                        'align': "center",
                        'bold': True,
                        'size': 1,
                    },

                    {
                        "type": "divider",
                    },


                    {
                        "type": "text",
                        "text": f"""{custome_wraper(configuration.address)}
{custome_wraper(configuration.tel)}
Email        : {configuration.email}
------------------------------------------------
Quotation #  : {quotation.ultimate_quotation_number}
Date         : {quotation.date_added}
Valid Until  : {quotation.expiration_date}
Currency     : {quotation.currency.currency}
Sales Rep    : {quotation.user.first_name.title()} {quotation.user.last_name.title()}
------------------------------------------------
VAT      :{configuration.vat_number}
TIN      :{configuration.tin_number}
PRZ      :{configuration.prz_number}
------------------------------------------------
                    BUYER
Buyer Name   : {quotation.customer.company_name if customer else ""}
Buyer TIN    : {quotation.customer.tin_number if customer else ""}
Buyer VAT    : {quotation.customer.vat_number if customer else ""}
Buyer Address: {custome_wraper(quotation.customer.address if customer else "")}

""",
                        "align": "left",
                    },

                    {
                        'type': "row",
                        'columns': [
                            {
                                'text': "Qty   Description",
                                'align': "left",
                                'bold': True,
                            },
                            {
                                'text': "Total Price",
                                'align': "right",
                                'bold': True,
                            },
                        ],
                    },

                    {
                        "type": "text",
                        "text": f"""------------------------------------------------""",
                        "align": "left",
                    },

                ]
            }

            # Get quotation items
            quotation = Quotation.objects.get(id=int(document_id))
            quotation_items = QuotationItem.objects.filter(quotation=quotation).select_related(
                'stock', 
                'stock__product',
                'stock__product__vat_code'
            )

            currency_rate = quotation.currency.rate
            subtotal = 0
            VAT = 0
            for item in quotation_items:
                item_subtotal = Decimal(str(item.unit_price)) * Decimal(str(item.quantity))
                subtotal += item_subtotal
                
                # Calculate VAT
                vat_percentage = Decimal('0.00')
                if item.stock and item.stock.product and item.stock.product.vat_code:
                    vat_percentage = Decimal(str(item.stock.product.vat_code.percentage))
                

                # Formula to extract VAT from an already inclusive subtotal
                item_vat = item_subtotal * (vat_percentage / (Decimal('100.00') + vat_percentage))

                VAT += item_vat

                # Apply currency conversion
                converted_total = item_subtotal * currency_rate

                document['content'].append({
                    'type': "row",
                    'columns': [
                        {
                            "text": f"{item.quantity} x ({str(item.stock.product.product_code)}) {str(item.stock.product.title)}",
                            "align": "left",
                        },
                        {
                            "text": f"{ locale.format_string('%.2f', converted_total, grouping=True) }",
                            "align": "right",
                        },
                    ],
                })


            discount = 0
            total_cost = subtotal


            
            suma = f"""

------------------------------------------------
{quotation.currency.shortcut} quotation.
{'Subtotal':<10}{ locale.format_string('%.2f', subtotal * currency_rate, grouping=True):>20}
{'Discount':<10}{ locale.format_string('%.2f', discount * currency_rate, grouping=True):>20}
{'VAT     ':<10}{ locale.format_string('%.2f', VAT * currency_rate, grouping=True):>20}
------------------------------------------------
{'Total   ':<10}{ locale.format_string('%.2f', total_cost * currency_rate, grouping=True):>20}
```````````````````````````````````````````````` """

            document['content'].append({
                    'type': "text",
                    'text': suma,
                    'align': "left",
               })

            document['content'].append({
                    'type': "text",
                    'text': f"""

BANKING DETAILS:
    Bank    : {branch.bank_1_bank_name}
    Acc     : {branch.bank_1_account_name}
    Nostro  : {branch.bank_1_nostro}
    ZiG     : {branch.bank_1_zig}

                    """,
                    'align': "left",
               })

            document['content'].append({
                    'type': "text",
                    'text': f"{branch.thank_you_message}",
                    'align': "center"
                })

            document['content'].append({
                    'type': "text",
                    'text': f"""


                    """,
                    'align': "center"
                })

        return print_document(
            printer,
            document,
        )


    elif document_type == "STOCKSUMMARY":
        from enventory.views import get_stock_value_summary

        summary_response = get_stock_value_summary(request)
        summary = json.loads(summary_response.content)

        document = {
            "type": "document",

            "printer_name": printer.name,

            "paper": {
                "width": 80,
                "cut": True,
                "copies": 1,
            },

            "content": [
                {
                    "type": "text",
                    "text": f"""------------------------------------------------
STOCK SUMMARY
------------------------------------------------
                    """,
                    "align": "center",
                },
                {
                    "type": "image",
                    "data": logo_data,
                    "align": "center",
                    "width": 350,
                },

                {
                    "type": "text",
                    "text": f"""{ configuration.company_name }""",
                    "align": "center",
                    "bold": True,
                    "size": 1,
                },

                {
                    "type": "text",
                    "text": f"""
------------------------------------------------
GENERATED   : {summary['generated_at']}
PREPARED BY : { request.user.first_name.title() } { request.user.first_name.title() }
------------------------------------------------
                    """,
                    "align": "left",
                },


                {
                    "type": "text",
                    "text": f"""
Total Products   :  {locale.format_string('%.0f', summary['total_products'], grouping=True):>20}
Selling Value    : ${locale.format_string('%.2f', summary['total_selling_value'], grouping=True):>20}
Profit Margin    : {locale.format_string('%.2f', summary['profit_margin_percentage'], grouping=True):>20}%
Profit Potential : ${locale.format_string('%.2f', summary['total_profit_potential'], grouping=True):>20}
Purchase Value   : ${locale.format_string('%.2f', summary['total_purchase_value'], grouping=True):>20}
Status           :  {locale.format_string('%.0f', summary['total_products'], grouping=True):>20} Active
Total Units      :  {locale.format_string('%.0f', summary['total_units'], grouping=True):>20}
Avg Value/Product: ${locale.format_string('%.2f', (summary['total_selling_value'] / summary['total_products'] if summary['total_products'] else 0), grouping=True):>20}

""",
                    "align": "left",
                },
            ]}

        document['content'].append({
            "type": "text",
            "text": f"""------------------------------------------------



***STAMP***



------------------------------------------------

""",
            "align": "center",
        })

        return print_document(
            printer,
            document,
        )


# ============================================================
# SIMPLE TEXT
# ============================================================

def print_text(
    printer,
    text,
):

    return send_to_print_server(

        server_ip=printer.get_resolved_ip(),  # Use resolved IP

        server_port=printer.server_port,

        printer_name=printer.name,

        print_type="text",

        text=text,

    )


# ============================================================
# GENERIC DOCUMENT
# ============================================================

def print_document(
    printer,
    document,
):
    """
    Send a generic document to the Windows Print Server.
    """

    if not isinstance(
        document,
        dict,
    ):

        return {

            "status": "error",

            "message": (
                "Document must be a dictionary."
            ),

        }

    if document.get(
        "type"
    ) != "document":

        return {

            "status": "error",

            "message": (
                "Document type must be 'document'."
            ),

        }

    content = document.get(
        "content"
    )

    if not isinstance(
        content,
        list,
    ):

        return {

            "status": "error",

            "message": (
                "Document content must be a list."
            ),

        }

    # ----------------------------------------------------------
    # Make a copy so the caller's object isn't modified.
    # ----------------------------------------------------------

    document = dict(
        document
    )

    document["printer_name"] = printer.name

    return send_to_print_server(

        server_ip=printer.get_resolved_ip(),  # Use resolved IP

        server_port=printer.server_port,

        printer_name=printer.name,

        print_type="document",

        document=document,

    )


# ============================================================
# LEGACY RECEIPT
# ============================================================

def print_receipt(
    printer,
    text1,
    text2,
    qr_data="",
    footer="",
    logo_data=None,
):
    """
    Legacy receipt interface.

    Kept for compatibility with existing code.
    """

    return send_to_print_server(

        server_ip=printer.get_resolved_ip(),  # Use resolved IP

        server_port=printer.server_port,

        printer_name=printer.name,

        print_type="full_receipt",

        text1=text1,

        text2=text2,

        qr_data=qr_data,

        footer=footer,

        logo_data=logo_data,

    )