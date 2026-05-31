'''
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
CLIENT: TAJO MOTOR SPARES
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
CLIENT: TAJO MOTOR SPARES
'''




import textwrap
try:
    import win32print
    import win32ui
    from PIL import Image, ImageWin
except ImportError:
    # win32 modules only exist on Windows; allow non-Windows dev to import this file
    win32print = None
    win32ui = None
    Image = None
    ImageWin = None

from payments.models import Sale, SaleTransaction, Payment
from accounts.models import ClientSetting, PrinterCase, CustomerAccount
from enventory.models import ReturnInn, CreditNote
from pos.models import QuotationItem, Quotation
from payments.models import PaymentMethod
from decimal import Decimal

from datetime import datetime

from reusable_functions.univesal.string_manipulation import custome_wraper, custom_html_wraper

import json
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse

from collections import defaultdict
from decimal import Decimal

import locale
locale.setlocale(locale.LC_ALL, '')

# configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
try:
    configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
except Exception as e:
    HttpResponseRedirect('client_settings_page')


def center_and_wrap(text, width=44):
    wrapped_text = textwrap.wrap(text, width=width)
    centeres_lines = [line.center(width) for line in wrapped_text]
    return centeres_lines


def print_logo(printer_name):
    PHYSICALWIDTH = 30
    PHYSICALHEIGHT = 30

    file_name = "logo.png"

    hDC = win32ui.CreateDC ()
    hDC.CreatePrinterDC (printer_name)
    printer_size = hDC.GetDeviceCaps (PHYSICALWIDTH), hDC.GetDeviceCaps (PHYSICALHEIGHT)

    bmp = Image.open (file_name)
    
    hDC.StartDoc (file_name)
    hDC.StartPage ()

    dib = ImageWin.Dib (bmp)
    dib.draw (hDC.GetHandleOutput (), (80,0,printer_size[0]+200,printer_size[1]+0))

    hDC.EndPage ()
    hDC.EndDoc ()
    hDC.DeleteDC ()







# ------------------------------------------------------------------------
# ------------------------------------------------------------------------
# ------------------------------------------------------------------------
# ------------------------------------------------------------------------
def print_out_credit_note_bulk(recipt_number, credit_note_id, receipt_purpose):
    try:
        sale_transaction = SaleTransaction.objects.get(recipt_number=recipt_number)

    except Exception as e:
        custome_status = "Error"
        message = f"{e}"

        return custome_status, message


    discount = sale_transaction.discount

    credit_note = CreditNote.objects.get(id=int(credit_note_id))

    # receiptmoneyportions = ReceiptMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to))
    receipt_money_portions = Payment.objects.filter(payment_for="RECEIPT", payment_for_id=int(sale_transaction.recipt_number))
    # refund_money_portions = RefundReturnInnMoneyPortion.objects.filter(credit_note=credit_note)
    refund_money_portions = Payment.objects.filter(payment_for="CREDIT_NOTE", payment_for_id=credit_note.id)

    dominant_money_portion = receipt_money_portions[0]
    dominant_money_portion_rate = dominant_money_portion.rate
    dominant_money_portion_shortcut = dominant_money_portion.payment_method.shortcut




    # REFUND PAYMENTS
    total_refunded_portions_portions_data_list = defaultdict(Decimal)

    for portion in refund_money_portions:
        total_refunded_portions_portions_data_list[portion.payment_method.shortcut] += portion.amount_paid


    total_refunded_portions_portions_data = ""
    for method, amount in total_refunded_portions_portions_data_list.items():
        amount = locale.format_string('%.2f', amount, grouping=True)
        total_refunded_portions_portions_data += f"{'':<5}{method:>20}{amount:>20}\n"


    # RECEIPT PAYMENTS 
    total_paid_portions_data_list = defaultdict(Decimal)

    for portion in receipt_money_portions:
        total_paid_portions_data_list[portion.payment_method.shortcut] += portion.amount_paid


    total_paid_portions_data = ""
    for method, amount in total_paid_portions_data_list.items():
        amount = locale.format_string('%.2f', amount, grouping=True)
        total_paid_portions_data += f"{'':<5}{method:>20}{amount:>20}\n"



    subtotal = 0
    VAT = 0
    bought_products_data = ""
    returned_products_data = ""

    sales = Sale.objects.filter(sale_transaction=sale_transaction)
    for sale in sales:
        subtotal += sale.quantity * sale.unit_price
        VAT += (sale.stock.product.vat_code.percentage/100) * (sale.quantity * sale.unit_price)

        bought_title_and_quantity = f"{sale.quantity} x ({str(sale.stock.product.product_code)}) {str(sale.stock.product.title)} "
        bought_products_data += f"{bought_title_and_quantity[:33]:<33}  {round(sale.selling_price * dominant_money_portion_rate,2) :>10}\n"


    returns_inn = ReturnInn.objects.filter(credit_note=credit_note)
    print("::::::::::::::::::::::::::::::::::::::::::::::JJJJJJJJJ")
    print(returns_inn)
    for return_inn in returns_inn:
        returned_title_and_quantity = f"{return_inn.total_units} x ({str(return_inn.sale.stock.product.product_code)}) {str(return_inn.sale.stock.product.title)} "
        returned_products_data += f"{returned_title_and_quantity[:33]:<33}  {round(return_inn.total_units * return_inn.sale.unit_price * dominant_money_portion_rate,2) :>10}\n"


    total_cost = (VAT + subtotal) - discount
    
    
    if receipt_purpose != " ":
        before_logo = f'''----------------------------------------------
                 CREDIT NOTE
----------------------------------------------
{' '.join(center_and_wrap(receipt_purpose))}

'''
    else:
        before_logo = f'''----------------------------------------------
                 CREDIT NOTE
----------------------------------------------

'''

    credit_note_text = f'''{' '.join(center_and_wrap(configuration.company_name))}\n

{custome_wraper(configuration.address)}
{custome_wraper(configuration.tel)}
Email    :{configuration.email}
----------------------------------------------
VAT          :{configuration.vat_number}
TIN          :{configuration.tin_number}
PRZ          :{configuration.prz_number}
Invoice     #:{sale_transaction.ultimate_recipt_number}
CREDIT NOTE #:{credit_note.ultimate_credit_note_number}
----------------------------------------------
                    BUYER
Buyer Name   :{sale_transaction.buyer_name}
Buyer Phone  :{sale_transaction.buyer_tel}
Buyer TIN    :{sale_transaction.buyer_tin}
Buyer VAT    :{sale_transaction.buyer_vat}
Buyer Address:{custome_wraper(sale_transaction.buyer_address)}
----------------------------------------------
Date     : {str(credit_note.created_at)[:16]}
Sales Rep: {credit_note.created_by.first_name.title()} {credit_note.created_by.last_name.title()}
----------------------------------------------
                    BOUGHT
{'Qty   Description':<34}{'Total Price':>10}

{bought_products_data}
----------------------------------------------\n
                   RETURNED
{'Qty   Description':<34}{'Total Price':>10}

{returned_products_data}
----------------------------------------------\n
                RETURN REASON
{ credit_note.reason.details}
{ credit_note.notes}
----------------------------------------------\n
{dominant_money_portion_shortcut} transaction.
{'Subtotal      ':<10}:{round(subtotal * dominant_money_portion_rate, 2):>10}
{'Discount      ':<10}:{round(discount * dominant_money_portion_rate, 2):>10}
{'VAT           ':<10}:{round(VAT * dominant_money_portion_rate, 2):>10}\n
----------------------------------------------
{'Total Paid    ':<10}:
{total_paid_portions_data}
{'TOTAL REFUNDED':<10}:
{total_refunded_portions_portions_data}

                BUYER'S SIGNATURE


          ............................

``````````````````````````````````````````````\n
     
{' '.join(center_and_wrap("YOUR CAR KNOWS THE BEST"))}  
    '''

    print(before_logo)
    print(credit_note_text)
    
    try:
        printer_name = PrinterCase.objects.filter(status=True)[0].printer_name #printers.recipt
        credit_note_text = credit_note_text + (8 * '\n') #recipt.text + (10 * '\n') for blank space at the bottom
        
        c_shap_cut_command = b"\x1B@\x1DV1"
        
        raw_data = bytes(credit_note_text , "utf-8")
        before_logo = bytes(before_logo, "utf-8")

        # create printer handle 
        import win32print
        drivers = win32print.EnumPrinterDrivers(None, None, 2)
        hPrinter = win32print.OpenPrinter(printer_name)
        printer_info = win32print.GetPrinter(hPrinter, 2)
        for driver in drivers:
            if driver["Name"] == printer_info["pDriverName"]:
                printer_driver = driver

        raw_type = "XPS_PASS" if printer_driver["Version"] == 4 else "RAW"

        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("test of raw data", None, raw_type))
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, before_logo)
                
            except Exception as e:
                
                #message.warning(request, f"Error! {e}")
                print(f"Error! {e}")
                message = f"Error printing! {e}"
                custome_status = "Error"
                return custome_status, message
            finally:
                win32print.EndDocPrinter(hPrinter)

            print_logo(printer_name)

            hJob = win32print.StartDocPrinter(hPrinter, 1, ("test of raw data", None, raw_type))
            try:
                win32print.WritePrinter(hPrinter, raw_data)
                win32print.EndPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, c_shap_cut_command)

            except Exception as e:
                
                #message.warning(request, f"Error! {e}")
                print(f"Error! {e}")
                message = f"Error printing! {e}"
                custome_status = "Error"
                return custome_status, message
            finally:
                win32print.EndDocPrinter(hPrinter)

                
        except Exception as e:
            
            # message.warning(request, f'Error! {e}')
            print(f"Error! {e}")
            message = f"Error! {e}"
            custome_status = "Error"
            return custome_status, message
        finally:
            win32print.ClosePrinter(hPrinter)

        # message.success(request, 'Printer job send')
        print('Printer job send')
        message = f"Printer job send"
        custome_status = ""
        return custome_status, message
        # -------------------------------------------------------------------
    except Exception as e:
        # message.warning(request, f"Error printing! {e}")
        print(f"Error printing! {e}")
        message = f"Error printing! {e}"
        custome_status = "Error"
        return custome_status, message

    message = "Transaction successful"
    custome_status = ""
    return custome_status, message



# ------------------------------------------------------------------------
# ------------------------------------------------------------------------
# ------------------------------------------------------------------------
# ------------------------------------------------------------------------






def print_credit_note(return_inn_id, receipt_purpose):
    try:
        return_inn = ReturnInn.objects.get(id=int(return_inn_id))
        sale_transaction = return_inn.sale.sale_transaction

    except Exception as e:
        custome_status = "Error"
        message = f"{e}"
        return custome_status, message



  

  

    print('----------------------------->>>')
    discount = sale_transaction.discount

    # dominant_money_portion = ReceiptMoneyPortion.objects.filter(sale_transaction=int(sale_transaction.recipt_number))[0]
    dominant_money_portion = Payment.objects.filter(payment_for="RECEIPT", payment_for_id=int(sale_transaction.recipt_number))[0]
    dominant_money_portion_rate = dominant_money_portion.rate
    dominant_money_portion_shortcut = dominant_money_portion.payment_method.shortcut



    sale = return_inn.sale

    subtotal = sale.quantity * sale.unit_price
    VAT = (sale.stock.product.vat_code.percentage/100) * (sale.quantity * sale.unit_price)

    bought_title_and_quantity = f"{sale.quantity} x ({str(sale.stock.product.product_code)}) {str(sale.stock.product.title)} "
    bought_products_data = f"{bought_title_and_quantity[:33]:<33}  {round(sale.selling_price * dominant_money_portion_rate,2) :>10}\n"

    returned_title_and_quantity = f"{return_inn.total_units} x ({str(return_inn.sale.stock.product.product_code)}) {str(return_inn.sale.stock.product.title)} "
    returned_products_data = f"{returned_title_and_quantity[:33]:<33}  {round(return_inn.total_units * return_inn.sale.unit_price * dominant_money_portion_rate,2) :>10}\n"

    print("---------------------------------------------------::::::::::::::::::::::@")
    print(return_inn.total_units)
    print(return_inn.sale.unit_price)
    print(dominant_money_portion_rate)
    print("---------------------------------------------------::::::::::::::::::::::@")

    total_cost = (VAT + subtotal) - discount
    
    
    if receipt_purpose != " ":
        before_logo = f'''----------------------------------------------
                 CREDIT NOTE
----------------------------------------------
{' '.join(center_and_wrap(receipt_purpose))}

'''
    else:
        before_logo = f'''----------------------------------------------
                 CREDIT NOTE
----------------------------------------------

'''

    credit_note_text = f'''{' '.join(center_and_wrap(configuration.company_name))}\n

{custome_wraper(configuration.address)}
{custome_wraper(configuration.tel)}
Email    :{configuration.email}
----------------------------------------------
VAT          :{configuration.vat_number}
TIN          :{configuration.tin_number}
PRZ          :{configuration.prz_number}
Invoice     #:{sale_transaction.ultimate_recipt_number}
CREDIT NOTE #:{return_inn.ultimate_credit_note_number}
----------------------------------------------
                    BUYER
Buyer Name   :{sale_transaction.buyer_name}
Buyer Phone  :{sale_transaction.buyer_tel}
Buyer TIN    :{sale_transaction.buyer_tin}
Buyer VAT    :{sale_transaction.buyer_vat}
Buyer Address:{custome_wraper(sale_transaction.buyer_address)}
----------------------------------------------
Date     : {str(return_inn.created_at)[:16]}
Sales Rep: {return_inn.created_by.first_name.title()} {return_inn.created_by.last_name.title()}
----------------------------------------------
                    BOUGHT
{'Qty   Description':<34}{'Total Price':>10}

{bought_products_data}
----------------------------------------------\n
                   RETURNED
{'Qty   Description':<34}{'Total Price':>10}

{returned_products_data}
----------------------------------------------\n
                RETURN REASON
{ return_inn.reason.details}
----------------------------------------------\n
{dominant_money_portion_shortcut} transaction.
{'Subtotal      ':<10}:{round(subtotal * dominant_money_portion_rate, 2):>10}
{'Discount      ':<10}:{round(discount * dominant_money_portion_rate, 2):>10}
{'VAT           ':<10}:{round(VAT * dominant_money_portion_rate, 2):>10}\n
----------------------------------------------
{'Total Paid    ':<10}:{round(total_cost * dominant_money_portion_rate, 2):>10}
{'TOTAL REFUNDED':<10}:{round(return_inn.refund_amount * dominant_money_portion_rate, 2):>10}

                BUYER'S SIGNATURE


          ............................

``````````````````````````````````````````````\n
     
{' '.join(center_and_wrap("YOUR CAR KNOWS THE BEST"))}  
    '''

    print(before_logo)
    print(credit_note_text)
    
    try:
        printer_name = PrinterCase.objects.filter(status=True)[0].printer_name #printers.recipt
        credit_note_text = credit_note_text + (8 * '\n') #recipt.text + (10 * '\n') for blank space at the bottom
        
        c_shap_cut_command = b"\x1B@\x1DV1"
        
        raw_data = bytes(credit_note_text , "utf-8")
        before_logo = bytes(before_logo, "utf-8")

        # create printer handle 
        import win32print
        drivers = win32print.EnumPrinterDrivers(None, None, 2)
        hPrinter = win32print.OpenPrinter(printer_name)
        printer_info = win32print.GetPrinter(hPrinter, 2)
        for driver in drivers:
            if driver["Name"] == printer_info["pDriverName"]:
                printer_driver = driver

        raw_type = "XPS_PASS" if printer_driver["Version"] == 4 else "RAW"

        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("test of raw data", None, raw_type))
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, before_logo)
                
            except Exception as e:
                
                #message.warning(request, f"Error! {e}")
                print(f"Error! {e}")
                message = f"Error printing! {e}"
                custome_status = "Error"
                return custome_status, message
            finally:
                win32print.EndDocPrinter(hPrinter)

            print_logo(printer_name)

            hJob = win32print.StartDocPrinter(hPrinter, 1, ("test of raw data", None, raw_type))
            try:
                win32print.WritePrinter(hPrinter, raw_data)
                win32print.EndPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, c_shap_cut_command)

            except Exception as e:
                
                #message.warning(request, f"Error! {e}")
                print(f"Error! {e}")
                message = f"Error printing! {e}"
                custome_status = "Error"
                return custome_status, message
            finally:
                win32print.EndDocPrinter(hPrinter)

                
        except Exception as e:
            
            # message.warning(request, f'Error! {e}')
            print(f"Error! {e}")
            message = f"Error! {e}"
            custome_status = "Error"
            return custome_status, message
        finally:
            win32print.ClosePrinter(hPrinter)

        # message.success(request, 'Printer job send')
        print('Printer job send')
        message = f"Printer job send"
        custome_status = ""
        return custome_status, message
        # -------------------------------------------------------------------
    except Exception as e:
        # message.warning(request, f"Error printing! {e}")
        print(f"Error printing! {e}")
        message = f"Error printing! {e}"
        custome_status = "Error"
        return custome_status, message

    message = "Transaction successful"
    custome_status = ""
    return custome_status, message


def print_quotation(user, currency_id, expiration_date, quotation_id, buyer_id):
    try:
        buyer = CustomerAccount.objects.get(id=int(buyer_id))
        buyer_name = buyer.company_name
        buyer_tin = buyer.tin_number

        buyer_prz = buyer.prz_number
        buyer_vat = buyer.vat_number
        buyer_address = buyer.address
    except:
        buyer_name = ""
        buyer_tin = ""
        buyer_prz = ""
        buyer_vat = ""
        buyer_address = f"""
             :"""

    try:
        # Get quotation items
        quotation = Quotation.objects.get(id=int(quotation_id))
        quotation_items = QuotationItem.objects.filter(quotation=quotation).select_related(
            'stock', 
            'stock__product',
            'stock__product__vat_code'
        )
        
        if not quotation_items.exists():
            return "Error", "error", "No items in quotation"
        
        # Initialize totals
        subtotal = Decimal('0.00')
        VAT = Decimal('0.00')
        
        # Get currency info
        currency_symbol = '$'
        currency_name = 'USD'
        currency_rate = Decimal('1.00')
        
        if currency_id and currency_id != '0':
            try:
                currency = PaymentMethod.objects.get(id=currency_id, status=True, deleted=False)
                currency_symbol = currency.shortcut
                currency_name = currency.currency
                currency_rate = Decimal(str(currency.rate)) if currency.rate else Decimal('1.00')
            except PaymentMethod.DoesNotExist:
                pass
        
        # Generate quotation number
        from datetime import datetime, timedelta

        quotation_number = f"QT-{datetime.now().strftime('%Y%m%d')}-{user.id:03d}"

        if not expiration_date:
            exp_date = (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")
        else:
            try:
                exp_date_obj = datetime.strptime(expiration_date, "%Y-%m-%d")
                exp_date = exp_date_obj.strftime("%d/%m/%Y")
            except:
                exp_date = expiration_date
        

        
        # Build products data
        products_data = ""
        for item in quotation_items:
            item_subtotal = Decimal(str(item.unit_price)) * Decimal(str(item.quantity))
            subtotal += item_subtotal
            
            # Calculate VAT
            vat_percentage = Decimal('0.00')
            if item.stock and item.stock.product and item.stock.product.vat_code:
                vat_percentage = Decimal(str(item.stock.product.vat_code.percentage))
            
            item_vat = item_subtotal * (vat_percentage / Decimal('100.00'))
            VAT += item_vat
            
            # Apply currency conversion
            converted_total = item_subtotal * currency_rate
            
            # Get product info
            product_code = item.stock.product.product_code if item.stock.product else "N/A"
            product_title = item.stock.product.title if item.stock.product else "Unknown Product"
            
            title_and_quantity = f"{item.quantity} x ({str(product_code)}) {str(product_title)}"
            products_data += f"{title_and_quantity[:33]:<33}  {round(converted_total, 2):>9.2f}\n"
        
        total_cost = subtotal + VAT
        
        # Apply currency conversion to totals
        converted_subtotal = subtotal * currency_rate
        converted_vat = VAT * currency_rate
        converted_total = total_cost * currency_rate
        
        # Quotation header
        before_logo = f'''----------------------------------------------
                  QUOTATION
----------------------------------------------
                                              
'''
        
        # Main receipt text
        company_header = f'''{' '.join(center_and_wrap(configuration.company_name))}\n
{custome_wraper(configuration.address)}
{custome_wraper(configuration.tel)}
Email    :{configuration.email}'''
        
        
        recipt_text = f'''{company_header}
----------------------------------------------
Quotation #: {quotation_number}
Date       : {datetime.now().strftime("%d/%m/%Y %H:%M")}
Valid Until: {exp_date}
Currency   : {currency_name}
Sales Rep  : {user.first_name.title()} {user.last_name.title()}
----------------------------------------------
VAT      :{configuration.vat_number}
TIN      :{configuration.tin_number}
PRZ      :{configuration.prz_number}
----------------------------------------------
                    BUYER
Buyer Name   :{buyer_name}
Buyer TIN    :{buyer_tin}
Buyer VAT    :{buyer_vat}
Buyer Address:{buyer_address}
----------------------------------------------
{'Qty   Description':<34}{'Total Price':>10}

{products_data}
----------------------------------------------
{currency_name} quotation.
{'Subtotal':<10}{currency_symbol}{round(converted_subtotal, 2):>9.2f}
{'VAT     ':<10}{currency_symbol}{round(converted_vat, 2):>9.2f}\n
----------------------------------------------
{'Total   ':<10}{currency_symbol}{round(converted_total, 2):>10.2f}
``````````````````````````````````````````````\n
     
BANKING DETAILS:
Bank  : CBZ
Acc   : TAJO MOTOR SPARES (PVT) LTD
Nostro: 09026668530024
ZiG   : 09026668530014

{' '.join(center_and_wrap("YOUR CAR KNOWS THE BEST"))} 
    '''
        
        print(before_logo)
        print(recipt_text)
        
        # Print to POS printer
        try:
            printer_name = PrinterCase.objects.filter(status=True)[0].printer_name
            recipt_text = recipt_text + (8 * '\n')
            
            c_shap_cut_command = b"\x1B@\x1DV1"
            
            raw_data = bytes(recipt_text, "utf-8")
            before_logo = bytes(before_logo, "utf-8")

            # Create printer handle
            import win32print
            drivers = win32print.EnumPrinterDrivers(None, None, 2)
            hPrinter = win32print.OpenPrinter(printer_name)
            printer_info = win32print.GetPrinter(hPrinter, 2)
            
            printer_driver = None
            for driver in drivers:
                if driver["Name"] == printer_info["pDriverName"]:
                    printer_driver = driver
                    break

            raw_type = "XPS_PASS" if printer_driver and printer_driver["Version"] == 4 else "RAW"

            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Quotation Print", None, raw_type))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, before_logo)
                    
                except Exception as e:
                    print(f"Error! {e}")
                    title = "Error"
                    type = "error"
                    message = f"Error printing! {e}"
                    return title, type, message
                finally:
                    win32print.EndDocPrinter(hPrinter)

                # Assuming print_logo function exists
                try:
                    print_logo(printer_name)
                except:
                    pass  # Skip logo if function doesn't exist or fails

                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Quotation Print", None, raw_type))
                try:
                    win32print.WritePrinter(hPrinter, raw_data)
                    win32print.EndPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, c_shap_cut_command)

                except Exception as e:
                    print(f"Error! {e}")
                    title = "Error"
                    type = "error"
                    message = f"Error printing! {e}"
                    return title, type, message
                finally:
                    win32print.EndDocPrinter(hPrinter)

            except Exception as e:
                print(f"Error! {e}")
                title = "Error"
                type = "error"
                message = f"Error! {e}"
                return title, type, message
            finally:
                win32print.ClosePrinter(hPrinter)

            print('Printer job sent')
            title = "Success"
            type = "success"
            message = f"Quotation {quotation_number} printed successfully"
            return title, type, message
            
        except Exception as e:
            print(f"Error printing! {e}")
            title = "Error"
            type = "error"
            message = f"Error printing! {e}"
            return title, type, message

    except Exception as e:
        print(f"General error: {e}")
        title = "Error"
        type = "error"
        message = str(e)
        return title, type, message


def print_receipt(sale_transaction_id, receipt_purpose):
    try:
        sale_transaction = SaleTransaction.objects.get(recipt_number=int(sale_transaction_id))
    except Exception as e:
        print(e)
        return JsonResponse({"custome_status": "Error", "message":f"{e}"})

    subtotal = 0 #sale_transaction.totals['subtotal']
    VAT = 0 #sale_transaction.totals['VAT']
    total_cost = 0 #sale_transaction.totals['total_cost']
    discount = sale_transaction.discount

    # dominant_money_portion = ReceiptMoneyPortion.objects.filter(sale_transaction=int(sale_transaction.recipt_number))[0]
    dominant_money_portion = Payment.objects.filter(payment_for="RECEIPT", payment_for_id=int(sale_transaction.recipt_number))[0]
    dominant_money_portion_rate = dominant_money_portion.rate
    dominant_money_portion_shortcut = dominant_money_portion.payment_method.shortcut


    products_data = ""
    sales = Sale.objects.filter(sale_transaction=int(sale_transaction.recipt_number))
    for sale in sales:
        subtotal += sale.quantity * sale.unit_price
        VAT += (sale.stock.product.vat_code.percentage/100) * (sale.quantity * sale.unit_price)

        title_and_quantity = f"{sale.quantity} x ({str(sale.stock.product.product_code)}) {str(sale.stock.product.title)} "
        products_data += f"{title_and_quantity[:33]:<33}  {round(sale.selling_price * dominant_money_portion_rate,2) :>10}\n"

    total_cost = (VAT + subtotal) - discount
    
    
    if receipt_purpose != " ":
        before_logo = f'''----------------------------------------------
            FISCAL TAX INVOICE
----------------------------------------------
{' '.join(center_and_wrap(receipt_purpose))}

'''
    else:
        before_logo = f'''----------------------------------------------
            FISCAL TAX INVOICE
----------------------------------------------

'''

    recipt_text = f'''{' '.join(center_and_wrap(configuration.company_name))}\n

{custome_wraper(configuration.address)}
{custome_wraper(configuration.tel)}
Email    :{configuration.email}
----------------------------------------------
VAT      :{configuration.vat_number}
TIN      :{configuration.tin_number}
PRZ      :{configuration.prz_number}
Invoice #: {sale_transaction.ultimate_recipt_number}
----------------------------------------------
                    BUYER
Buyer Name   :{sale_transaction.buyer_name}
Buyer TIN    :{sale_transaction.buyer_tin}
Buyer VAT    :{sale_transaction.buyer_vat}
Buyer Address:{custome_wraper(sale_transaction.buyer_address)}
----------------------------------------------
Date     : {str(sale_transaction.created_at)[:16]}
Sales Rep: {sale_transaction.created_by.first_name.title()} {sale_transaction.created_by.last_name.title()}
----------------------------------------------
{'Qty   Description':<34}{'Total Price':>10}

{products_data}
----------------------------------------------\n
{dominant_money_portion_shortcut} transaction.
{'Subtotal':<10}{round(subtotal * dominant_money_portion_rate, 2):>10}
{'Discount':<10}{round(discount * dominant_money_portion_rate, 2):>10}
{'VAT     ':<10}{round(VAT * dominant_money_portion_rate, 2):>10}\n
----------------------------------------------
{'Total   ':<10}{round(total_cost * dominant_money_portion_rate, 2):>10}
``````````````````````````````````````````````\n
     
{' '.join(center_and_wrap("YOUR CAR KNOWS THE BEST"))}  
    '''

    print(before_logo)
    print(recipt_text)
    
    try:
        printer_name = PrinterCase.objects.filter(status=True)[0].printer_name #printers.recipt
        recipt_text = recipt_text + (8 * '\n') #recipt.text + (10 * '\n') for blank space at the bottom
        
        c_shap_cut_command = b"\x1B@\x1DV1"
        
        raw_data = bytes(recipt_text , "utf-8")
        before_logo = bytes(before_logo, "utf-8")

        # create printer handle 
        import win32print
        drivers = win32print.EnumPrinterDrivers(None, None, 2)
        hPrinter = win32print.OpenPrinter(printer_name)
        printer_info = win32print.GetPrinter(hPrinter, 2)
        for driver in drivers:
            if driver["Name"] == printer_info["pDriverName"]:
                printer_driver = driver

        raw_type = "XPS_PASS" if printer_driver["Version"] == 4 else "RAW"

        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("test of raw data", None, raw_type))
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, before_logo)
                
            except Exception as e:
                
                #message.warning(request, f"Error! {e}")
                print(f"Error! {e}")
                message = f"Error printing! {e}"
                custome_status = "Error"
                return custome_status, message
            finally:
                win32print.EndDocPrinter(hPrinter)

            print_logo(printer_name)

            hJob = win32print.StartDocPrinter(hPrinter, 1, ("test of raw data", None, raw_type))
            try:
                win32print.WritePrinter(hPrinter, raw_data)
                win32print.EndPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, c_shap_cut_command)

            except Exception as e:
                
                #message.warning(request, f"Error! {e}")
                print(f"Error! {e}")
                message = f"Error printing! {e}"
                custome_status = "Error"
                return custome_status, message
            finally:
                win32print.EndDocPrinter(hPrinter)

                
        except Exception as e:
            
            # message.warning(request, f'Error! {e}')
            print(f"Error! {e}")
            message = f"Error! {e}"
            custome_status = "Error"
            return custome_status, message
        finally:
            win32print.ClosePrinter(hPrinter)

        # message.success(request, 'Printer job send')
        print('Printer job send')
        message = f"Printer job send"
        custome_status = ""
        return custome_status, message
        # -------------------------------------------------------------------
    except Exception as e:
        # message.warning(request, f"Error printing! {e}")
        print(f"Error printing! {e}")
        message = f"Error printing! {e}"
        custome_status = "Error"
        return custome_status, message

    message = "Transaction successful"
    custome_status = ""
    return custome_status, message



def print_formated_text(text):
    try:
        printer_name = PrinterCase.objects.filter(status=True)[0].printer_name #printers.recipt
        text = text + (8 * '\n') #recipt.text + (10 * '\n') for blank space at the bottom
        
        c_shap_cut_command = b"\x1B@\x1DV1"
        
        raw_data = bytes(text , "utf-8")

        # create printer handle 
        
        drivers = win32print.EnumPrinterDrivers(None, None, 2)
        hPrinter = win32print.OpenPrinter(printer_name)
        printer_info = win32print.GetPrinter(hPrinter, 2)
        for driver in drivers:
            if driver["Name"] == printer_info["pDriverName"]:
                printer_driver = driver

        raw_type = "XPS_PASS" if printer_driver["Version"] == 4 else "RAW"

        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("test of raw data", None, raw_type))
            try:
                win32print.WritePrinter(hPrinter, raw_data)
                win32print.EndPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, c_shap_cut_command)

            except Exception as e:
                
                #message.warning(request, f"Error! {e}")
                print(f"Error! {e}")
                custome_status = "Error"
                message = f"Error! {e}"

            finally:
                win32print.EndDocPrinter(hPrinter)

                
        except Exception as e:
            
            # message.warning(request, f'Error! {e}')
            print(f"Error! {e}")
            custome_status = "Error"
            message = f"Error! {e}"
        finally:
            win32print.ClosePrinter(hPrinter)

        # message.success(request, 'Printer job send')
        print('Printer job send')
        custome_status = ""
        message = f"Printer job send!"
        return custome_status, message

        # -------------------------------------------------------------------
    except Exception as e:
        # message.warning(request, f"Error printing! {e}")
        print(f"Error printing! {e}")
        custome_status = "Error"
        message = f"Error! {e}"
        return custome_status, message



