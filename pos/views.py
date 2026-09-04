from decimal import Decimal

from django.views.decorators.csrf import csrf_exempt

from django.shortcuts import render, redirect

from rest_framework import viewsets

from django.contrib.auth.decorators import login_required


from django.http import HttpResponse, HttpResponseRedirect, JsonResponse

from reusable_functions.univesal.fiscalisation import get_fiscal_details, is_correct_hs_code_format

from rest_framework.decorators import api_view

from rest_framework.response import Response
from rest_framework import status


from rest_framework.exceptions import APIException
from enventory.models import *
from accounts.models import *
from order.models import *
from .models import CartItem, ReceiptPaymentEssential
from payments.models import SaleTransaction, Sale, PaymentMethod, Payment

from django.db.models import Sum, F
from django.db import transaction

import json

from .models import QuotationItem, Quotation

from reusable_functions.univesal.time_and_dates import days_from_now_python



import locale
locale.setlocale(locale.LC_ALL, '') 

from datetime import datetime as datetime_

from reusable_functions.univesal.decorators import role_validator
from reusable_functions.univesal.notifications import stock_quantity_notification
from reusable_functions.univesal.client_spacific_functions.client_spacific_functions import print_receipt, print_quotation
from reusable_functions.univesal.string_manipulation import custom_html_wraper
from django.contrib.auth.decorators import login_required






class InsufficientStockError(Exception):
    def __init__(self, message):
        self.message = message

try:
    configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
    pagination_slice_leangth = configuration.pagination_slice_leangth
except Exception as e:
    HttpResponseRedirect('client_settings_page')

# --------------------------------------------------------------------
# POS PAGE
# --------------------------------------------------------------------
@login_required
@role_validator(['Sales Rep'])
def pos(request):
    return render(request, 'pos/pos.html')


# --------------------------------------------------------------------
# //POS PAGE
# --------------------------------------------------------------------




# --------------------------------------------------------------------
# EXCLUSIVE QUTATIONS
# --------------------------------------------------------------------


# views.py
from django.shortcuts import render
from django.utils import timezone
from datetime import datetime, timedelta

from django.shortcuts import render
from datetime import datetime, timedelta

from decimal import Decimal

import locale
locale.setlocale(locale.LC_ALL, '') 

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger




def ajax_quotations_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')
    quotation_number = request.GET.get('quotation_number')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        quotations = Quotation.objects.all().order_by('-date_added')


    if request_type == "FORM-FILTER":
        # form filterr here
        quotations = Quotation.objects.all().order_by('-date_added')
        quotations = quotations.filter(id__contains=quotation_number)

    
    #------------------------------------------------------------------------------ 
    data_queryset = quotations
    paginator = Paginator(data_queryset, pagination_slice_leangth)  # Load 20 items per page
    page = request.GET.get('page')
    # page = 1


    try:
        data_page = paginator.page(page)
    except PageNotAnInteger:
        data_page = paginator.page(1)
    except EmptyPage:
        data_page = paginator.page(paginator.num_pages)

    #------------------------------------------------------------------------------

    table_header = """
        <thead >
            <tr style="background-color:rgb(0,194,146);" class="sticky-top top-0">
                <th>Quote #</th>
                <th>Details</th>
                <th style="text-align: center">Total Items</th>
                <th style="text-align: right">Total Price</th>
                <th>Action</th>
            </tr>
        </thead>
    """
    rows = ""
    for quotation in data_page:
        row = f"""
            <tr>
                <td><b>{ quotation.ultimate_quotation_number }</b></td>
                <td>{ str(quotation.date_added.strftime("%a, %d %b %Y")) } | <span style="color: red;">{ str(quotation.expiration_date.strftime("%a, %d %b %Y")) }</span><br>
                    <small>
                        Customer | { quotation.customer.company_name if quotation.customer else None}<br>
                        Sales Rep | { quotation.user.first_name.title() } { quotation.user.last_name.title() }<br>
                        Status | <span style="background: { quotation.color }; padding: 5px; color: white; border-radius: 15px;"> { quotation.status }</span><br>
                    </small>
                </td>
                <td style="text-align: center">{ locale.format_string('%.0f',quotation.total_items, grouping=True) }</td>
                <td style="text-align: right">{ locale.format_string('%.2f', quotation.total_price, grouping=True) }</td>
                <td style="text-align: right;"><a href='/pos/create_quotation_page/{ quotation.id }' class='button btn'">📝</a></td>
            </tr>
        """
        rows += row

    table_body = f"""
        <tbody class="" style="height:200px">
            {rows}
    """

    table_footer = """
            <tr style="background-color:rgb(0,194,146);">
                <td>Total</td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer


    table_summery = f" {quotations.count()} out of {Quotation.objects.all().count()} batch adjustment reasons."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})



def quotations_page(request):
    return render(request, 'pos/quotations_page.html')


def create_quotation_page(request, pk=None):
    if pk == None:
        pk = 0

    try:
        quotation = Quotation.objects.get(id=int(pk))
        quotation_number = quotation.ultimate_quotation_number
    except Quotation.DoesNotExist:
        empty_qutation = Quotation.objects.filter(user=request.user, just_created=True).last()
        if empty_qutation:
            quotation = empty_qutation
            quotation_number = quotation.ultimate_quotation_number
            pk = quotation.id
            return HttpResponseRedirect(f'/pos/create_quotation_page/{pk}')

        else:
            new_quotation = Quotation()
            new_quotation.user = request.user
            new_quotation.expiration_date = days_from_now_python(14)
            new_quotation.save()
            quotation = new_quotation
            quotation_number = quotation.ultimate_quotation_number
            pk = quotation.id
            return HttpResponseRedirect(f'/pos/create_quotation_page/{pk}')

    except Exception as e:
        pass
        # something need to be done here
    

    context = {
        'quotation_id': pk,
        'quotation_number': quotation_number,
    }
    return render(request, 'pos/create_quotation_page.html', context)


def print_quotation_in_pos_printer(request):
    currency_id = request.GET.get('currency_id')
    quotation_id = request.GET.get('quotation_id')
    buyer_id = request.GET.get('buyer_id')
    expiration_date = request.GET.get('expiration_date')

    title, type, message = print_quotation(request.user, currency_id, expiration_date, quotation_id, buyer_id)

    return JsonResponse({"type":type, "title":title, "message":message})


@transaction.atomic
def copy_quotation_to_cart(request):
    try:
        quotation_id = request.POST.get('quotation_id')
        quotation = Quotation.objects.get(id=int(quotation_id))

        quotation_items = QuotationItem.objects.filter(quotation=quotation)
        if quotation_items.count() < 1:
            return JsonResponse({"icon":"error", "title":"Empty Quotation", "message":"Nothing happened, your quotation is empty!"})


        user = request.user
        for item in quotation_items:
            stock_id = item.stock.id
            quantity = item.quantity
            unit_price = item.unit_price
            message = add_quotation_item_to_cart(request, stock_id, quantity, unit_price)

        return JsonResponse({"icon":"success", "title":"Succesfully", "message":"Note that, if a product is quoted more items that available in stock, the intire line is skiped, hence, you will have to add it manualy"})
    
    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})



@login_required
@transaction.atomic
def add_quotation_item_to_cart(request, stock_id, quantity, unit_price):
    try:
        user = request.user
        stock = Stock.objects.get(id=stock_id)
        stock_cart_item_already_exist = CartItem.objects.filter(stock=stock, user=user)
        if stock_cart_item_already_exist:
            old_item = stock_cart_item_already_exist[0]
            current_cart_item = old_item

            current_cart_item.unit_price = float(unit_price)
            current_cart_item.quantity = float(current_cart_item.quantity) + float(quantity)
            current_cart_item.VAT = float(stock.selling_price * stock.product.vat_code.percentage/100) * quantity

        else:
            new_cart_item = CartItem()
            new_cart_item.stock = stock
            new_cart_item.unit_price = stock.selling_price
            new_cart_item.quantity = quantity
            new_cart_item.VAT = (stock.selling_price * stock.product.vat_code.percentage/100) * quantity
            new_cart_item.buying_unit_price = stock.avarage_unit_cost
            new_cart_item.user = request.user
            new_cart_item.used_baches_data = ""
            new_cart_item.used_baches_quantities_data = ""
            # new_cart_item.save()

            current_cart_item = new_cart_item

        
        batch_ids = []

        #collecting all batch ids that can be used
        available_for_sale_batches = Batch.objects.filter(status=True, stock=stock, total_units__gte=0)
        for batch in available_for_sale_batches:
            batch_ids.append(batch.id)

        requared_quntity = quantity
        #check if there are enogh products
        total_units_available_for_sale = 0
        for batch in available_for_sale_batches:
            total_units_available_for_sale += batch.total_units

        if total_units_available_for_sale >= requared_quntity:
            #altering batches quntities and deactivating empty ones
            actively_requred_quantity = requared_quntity
            still_needed = True
            for batch in available_for_sale_batches:
                if still_needed:
                    pass
                else:
                    break

                if batch.total_units - actively_requred_quantity >= 0:
                    batch.total_units = batch.total_units - actively_requred_quantity
                    batch.save()
                    still_needed = False
                    current_cart_item.used_baches_data += f"{batch.id},"
                    current_cart_item.used_baches_quantities_data += f"{actively_requred_quantity},"
                else:
                    actively_requred_quantity -= batch.total_units
                    available_in_batch = batch.total_units
                    batch.total_units = 0
                    # batch.status = False
                    batch.save()
                    current_cart_item.used_baches_data += f"{batch.id},"
                    current_cart_item.used_baches_quantities_data += f"{available_in_batch},"

            current_cart_item.save()


            message = "Added succesfully"
            return message


        else:
            print(f"available not enough -------------------------------------{total_units_available_for_sale}")

            message = (f"Not enough products in stock. Available units for this item: {total_units_available_for_sale}")

        return message

    except Exception as e:
        return str(e)



def quotation_print_view(request):
    """Render quotation print template"""
    # Get parameters
    currency_id = request.GET.get('currency_id', '0')
    expiration_date = request.GET.get('expiration_date', '')
    buyer_id = request.GET.get('buyer_id', '0')
    quotation_id = request.GET.get('quotation_id', '0')

    
    # Get quotation items with related data
    quotation = Quotation.objects.get(id=int(quotation_id))
    quotation_items = QuotationItem.objects.filter(quotation=quotation).select_related(
        'stock', 
        'stock__product',
        'stock__product__vat_code'
    )
    
    # Get currency info with rate
    currency_symbol = '$'
    currency_name = 'USD'
    currency_rate = Decimal('1.0')  # Default rate for base currency
    
    if currency_id != '0':
        try:
            currency = PaymentMethod.objects.get(id=currency_id, status=True, deleted=False)
            currency_symbol = currency.shortcut
            currency_name = currency.currency
            currency_rate = Decimal(str(currency.rate)) if currency.rate else Decimal('1.0')
        except PaymentMethod.DoesNotExist:
            pass
    
    # Calculate totals with VAT and currency conversion
    base_subtotal = Decimal('0.00')
    base_vat_total = Decimal('0.00')
    items_data = []
    
    for item in quotation_items:
        # Calculate in base currency first
        item_base_subtotal = Decimal(str(item.unit_price)) * Decimal(str(item.quantity))
        base_subtotal += item_base_subtotal
        
        # Get VAT percentage for this item
        vat_percentage = Decimal('0.00')
        if item.stock and item.stock.product and item.stock.product.vat_code:
            vat_percentage = Decimal(str(item.stock.product.vat_code.percentage))
        
        # Calculate VAT in base currency
        item_base_vat = item_base_subtotal * (vat_percentage / Decimal('100.00'))
        base_vat_total += item_base_vat
        
        # Convert to selected currency
        item_converted_subtotal = item_base_subtotal * currency_rate
        item_converted_vat = item_base_vat * currency_rate
        
        items_data.append({
            'title': item.stock.product.title,
            'details': item.stock.product.details,
            'quantity': item.quantity,
            'unit_price': float(Decimal(str(item.unit_price)) * currency_rate),  # Converted unit price
            'base_unit_price': float(item.unit_price),  # Original unit price
            'unit_vat_percentage': float(vat_percentage),
            'total': float(item_converted_subtotal),  # Converted total
            'vat': float(item_converted_vat),  # Converted VAT
            'base_total': float(item_base_subtotal),  # Base currency total
            'base_vat': float(item_base_vat),  # Base currency VAT
        })
    
    # Convert totals to selected currency
    converted_subtotal = base_subtotal * currency_rate
    converted_vat_total = base_vat_total * currency_rate
    converted_total = converted_subtotal + converted_vat_total

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
        buyer_address = ""    
    # Prepare context with TAJO MOTOR SPARES details
    context = {
        'items': items_data,
        'subtotal': float(converted_subtotal),
        'vat': float(converted_vat_total),
        'total': float(converted_total),
        'currency_symbol': currency_symbol,
        'currency': currency_name,
        'currency_rate': float(currency_rate),
        'base_currency_symbol': '$',  # Assuming USD is base currency
        'base_subtotal': float(base_subtotal),
        'base_vat': float(base_vat_total),
        'base_total': float(base_subtotal + base_vat_total),
        'date': datetime.now().strftime("%d %B, %Y"),
        'expiration_date': expiration_date or (datetime.now() + timedelta(days=30)).strftime("%d %B, %Y"),
        'quotation_number': f"QT-{datetime.now().strftime('%Y%m%d')}-{request.user.id:03d}",
        
        # TAJO MOTOR SPARES Company info
        'company_name': configuration.company_name,
        'company_address': configuration.address,
        'company_phone': configuration.tel,
        'company_email': configuration.email,
        'vat_number': configuration.vat_number,
        'tin_number': configuration.tin_number,
        'prz_number': configuration.prz_number,
        'logo_url': '/static/images/logo.jpg',
        
        # Banking Details
        'bank_name': configuration.bank_1_bank_name,
        'account_name': configuration.bank_1_account_name,
        'nostro_account': configuration.bank_1_name_nostro,
        'zig_account': configuration.bank_1_name_zig,
        
        # Customer info
        'buyer_name': buyer_name,
        'buyer_tin': buyer_tin,
        'buyer_prz': buyer_prz,
        'buyer_vat': buyer_vat,
        'buyer_address': buyer_address,

        # Authorized signature
        'authorized_signature': f'{request.user.first_name.title()} {request.user.last_name.title()} ',

        
        # Exchange rate display
        'show_exchange_rate': currency_rate != Decimal('1.0'),
    }
    
    return render(request, 'pos/quotation_template.html', context)


@transaction.atomic
def delete_quotation_item(request):
    try:
        if request.method == 'POST':
            item_id = request.POST.get('item_id')

            try:
                item = QuotationItem.objects.get(
                    id=item_id,
                    user=request.user
                )
                item.delete()

                return JsonResponse({
                    'title': 'Deleted!',
                    'message': 'Item removed from quotation'
                })

            except QuotationItem.DoesNotExist:
                return JsonResponse({
                    'type': 'error',
                    'message': 'Item not found'
                })

        return JsonResponse({'type': 'error', 'message': 'Invalid request'})

    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})


@transaction.atomic
def clear_quotation_items(request):
    try:
        """Clear all quotation items for current user"""
        quotation_id = request.POST.get('quotation_id')

        try:
            quotation = Quotation.objects.get(id=int(quotation_id))
            if quotation.user == request.user:
                pass
            else:
                return JsonResponse({"icon":'error', "title":'Permission Denied', "message":"You are not authorised to update this quotation."})
                
        except Quotation.DoesNotExist:
            return JsonResponse({"icon": 'error', 'type': 'error', 'message': 'This invoice dose not exist'})


        if request.method == 'POST':
            try:
                deleted_count = QuotationItem.objects.filter(quotation=quotation).delete()[0]
                
                return JsonResponse({
                    'success': True,
                    'title': 'Cleared!',
                    'message': f'Removed {deleted_count} items from quotation'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'title': 'Error',
                    'message': str(e)
                })
        
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})



def get_quotation_data_exclusive(request):
    # Get currency from request
    currency_id = request.GET.get('currency_id', '0')
    quotation_id = request.GET.get('quotation_id')
    quotation = Quotation.objects.get(id=int(quotation_id))
    
    # Default currency
    rate = Decimal('1.00')
    symbol = '$'
    
    # If currency selected, get its rate
    if currency_id != '0':
        try:
            currency = PaymentMethod.objects.get(id=currency_id, status=True, deleted=False)
            rate = currency.rate
            symbol = currency.shortcut
        except:
            pass  # Keep defaults if currency not found
    
    # Get items for current user
    items = QuotationItem.objects.filter(quotation=quotation)

    
    # Calculate totals
    subtotal = Decimal('0')
    items_list = []
    
    for item in items:
        # Calculate item total
        item_total = item.unit_price * item.quantity * rate
        
        # Add to subtotal
        subtotal += item.unit_price * item.quantity
        
        # Add to items list (with converted price)
        items_list.append({
            'id': item.id,
            'product_code': item.stock.product.product_code,
            'title': item.stock.product.title,
            'details': item.stock.product.details,
            'quantity': item.quantity,
            'total': str(item_total)  # Converted total
        })
    
    # Convert subtotal
    subtotal_converted = subtotal * rate
    
    # Calculate VAT (16%) and total (converted)
    vat = subtotal_converted * Decimal('0')
    total = subtotal_converted + vat
    
    # Return JSON response
    return JsonResponse({
        'items': items_list,
        'subtotal': str(subtotal_converted),
        'vat': str(vat),
        'total': str(total),
        'currency': symbol
    })



@transaction.atomic
def add_quotation_item(request):
    try:
        stock_id = request.POST.get('stock_id')
        quantity = request.POST.get('quantity')
        unit_price = request.POST.get('unit_price')
        quotation_id = request.POST.get('quotation_id')

        try:
            quotation = Quotation.objects.get(id=int(quotation_id))
            if quotation.user == request.user:
                pass
            else:
                return JsonResponse({"icon":'error', "title":'Permission Denied', "message":"You are not authorised to update this quotation."})
                
        except Quotation.DoesNotExist:
            print('>>>>>>>>>>>>>')
            new_quotation = Quotation()
            new_quotation.expiration_date = days_from_now_python(14)
            new_quotation.user = request.user
            new_quotation.save()


            quotation = new_quotation

        except Exception as e:
            print(e)
            return JsonResponse({"icon":'error', "type": 'error', "title":'Permission Denied', "message":f"{e}"})
            

        stock = Stock.objects.get(id=stock_id)



        already_exist = QuotationItem.objects.filter(quotation=quotation, stock__id=int(stock_id), user=request.user).first()
        if already_exist:
            quotation_item = already_exist
            quotation_item.quantity += int(quantity)
            quotation_item.unit_price = float(unit_price)
            quotation_item.save()

            return JsonResponse({"icon":'success', "title":'Updated', "message":"Item updated succesfully"})

        else:
            quotation_item = QuotationItem()
            quotation_item.quotation = quotation
            quotation_item.stock = stock
            quotation_item.quantity = int(quantity)
            quotation_item.unit_price = float(unit_price)
            quotation_item.user = request.user
            quotation_item.save()

            if quotation.just_created:
                quotation.just_created = False
                quotation.save()

            return JsonResponse({"icon":'success', "title":'Added', "message":"Item added succesfully"})

    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})
        
    



# --------------------------------------------------------------------
# EXCLUSIVE QUTATIONS
# --------------------------------------------------------------------



# --------------------------------------------------------------------
# AJAX
# --------------------------------------------------------------------

@login_required
def get_quotation_data(request):
    cart_items = CartItem.objects.filter(user=request.user)
    payment_method_id = request.GET.get('payment_method_id')

    rate = 1
    currency_text = "____________________"
    try:
        payment_method = PaymentMethod.objects.get(id=int(payment_method_id))
        rate = payment_method.rate
        currency_text = payment_method.shortcut
    except:
        pass

    try:
        configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
        company_name = configuration.company_name
        address = custom_html_wraper(configuration.address)
        phone_number = configuration.tel
        email = configuration.email

        tin_number = configuration.tin_number
        prz_number = configuration.prz_number
        vat_number = configuration.vat_number

        bank_1_bank_name = configuration.bank_1_bank_name
        bank_1_account_name = configuration.bank_1_account_name
        bank_1_name_nostro = configuration.bank_1_name_nostro
        bank_1_name_zig = configuration.bank_1_name_zig

    except:
        company_name = ""
        address = ""
        phone_number = ""
        email = ""

        tin_number = ""
        prz_number = ""
        vat_number = ""

        bank_1_bank_name = ""
        bank_1_account_name = ""
        bank_1_name_nostro = ""
        bank_1_name_zig = ""

    subtotal = 0
    VAT = 0
    total_cost = 0
    table_header = f"""
        <tr>
            <td colspan="5"><hr></td>
        </tr>
        <tr>
            <th>Product</th>
            <th style="text-align: right">Unit Price</th>
            <th style="text-align: right">Quantity</th>
            <th style="text-align: right">VAT</th>
            <th style="text-align: right">Total</th>
        </tr>
        <tr>
            <td colspan="5"><hr></td>
        </tr>
    """

    table_rows = table_header
    for cart_item in cart_items:

        subtotal = subtotal + (cart_item.unit_price * cart_item.quantity)
        VAT = VAT + cart_item.VAT
        total_cost = total_cost +  ((cart_item.unit_price * cart_item.quantity) + cart_item.VAT)

        row = f"""
            <tr>
                <td style="width:50%">{ cart_item.stock.product.title } { cart_item.stock.product.details }</td>
                <td style="text-align: right; width:12%">{ locale.format_string('%.2f', cart_item.unit_price * rate, grouping=True) }</td>
                <td style="text-align: right; width:10%">{ locale.format_string('%.0f', cart_item.quantity * rate, grouping=True) }</td>
                <td style="text-align: right; width:13%">{ locale.format_string('%.2f', cart_item.VAT * rate, grouping=True) }</td>
                <td style="text-align: right; width:15%">{ locale.format_string('%.2f', ((cart_item.unit_price * cart_item.quantity) + cart_item.VAT) * rate, grouping=True) }</td>
            </tr>
            <tr>
                <td colspan="5"><hr></td>
            </tr>
        """
        table_rows += row

    date = str(datetime_.today().date())[:10]

    details = {
        "company_name": company_name,
        "address": address,
        "phone_number": phone_number,
        "email": email,

        "date": date,
        "cashier": f"{request.user.first_name.title() } {request.user.last_name.title() }",

        "tin_number": tin_number,
        "prz_number": prz_number,
        "vat_number": vat_number,

        "bank_1_bank_name": bank_1_bank_name,
        "bank_1_account_name": bank_1_account_name,
        "bank_1_name_nostro": bank_1_name_nostro,
        "bank_1_name_zig": bank_1_name_zig
    }

    totals = {
        "currency_text": currency_text,
        "subtotal": locale.format_string('%.2f', subtotal * rate, grouping=True),
        "VAT": locale.format_string('%.2f', VAT * rate, grouping=True),
        "total_cost": locale.format_string('%.2f', total_cost * rate, grouping=True)
    }
    return JsonResponse({"details": details, "totals": totals, "table_rows": table_rows})

@role_validator(['Sales Rep'])
@transaction.atomic
def delete_cart_item(request):
    try:
        cart_item_id = int(request.GET.get('cart_item_id')) 
        single_or_all = "Single"
        custome_status, message = remove_item_from_cart(single_or_all, cart_item_id)
        return JsonResponse({"custome_status": custome_status, "message": message})
    
    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})


@transaction.atomic
def remove_item_from_cart(single_or_all, user_id_or_item_id):
    try:
        # deleting a single cart item
        if single_or_all == "Single":
            cart_item_id = user_id_or_item_id
            try:
                cart_items = CartItem.objects.filter(id=int(cart_item_id))
                for cart_item in cart_items:
                    used_batches_ids = cart_item.used_baches_data.rstrip(",").split(",")
                    used_baches_quantities = cart_item.used_baches_quantities_data.rstrip(",").split(",")
                    #returning data on void 
                    for i in range(len(used_batches_ids)):
                        batch = Batch.objects.get(id=int(used_batches_ids[i]))
                        quantity = int(used_baches_quantities[i])

                        batch.total_units += quantity
                        batch.status = True
                        batch.save()

                    cart_item.delete()
                

                # return JsonResponse({"custome_status": "", "message":"Cart cleared succesfully"})
                custome_status = ""
                message = "Cart cleared succesfully"
                print(f"{message} --------------------------------------------------- @@@@@")
                return custome_status, message


            except Exception as e:
                # return JsonResponse({"custome_status": "Error", "message":str(e)})
                custome_status = "Error"
                message = str(e)
                print(f"{message} --------------------------------------------------- @@@@@")
                return custome_status, message


            

        # deleting the whole cart
        elif single_or_all == "All":
            user_id = user_id_or_item_id
            try:
                cart_items = CartItem.objects.filter(user=int(user_id))
                for cart_item in cart_items:
                    used_batches_ids = cart_item.used_baches_data.rstrip(",").split(",")
                    used_baches_quantities = cart_item.used_baches_quantities_data.rstrip(",").split(",")
                    #returning data on void 
                    for i in range(len(used_batches_ids)):
                        batch = Batch.objects.get(id=int(used_batches_ids[i]))
                        quantity = int(used_baches_quantities[i])

                        batch.total_units += quantity
                        batch.status = True
                        batch.save()

                    cart_item.delete()
                

                # return JsonResponse({"custome_status": "", "message":"Cart cleared succesfully"})
                custome_status = ""
                message = "Cart cleared succesfully"
                print(f"{message} ----------------------------------->>> ")
                return custome_status, message


            except Exception as e:
                # return JsonResponse({"custome_status": "Error", "message":str(e)})
                custome_status = "Error"
                message = str(e)
                print(f"{message} ----------------------------------->>> ")
                return custome_status, message

        else:
            custome_status = "Error"
            message = "Something seriosly wrong is going on. Contact Avail ASAP"
            print(f"{message} ----------------------------------->>> ")
            return custome_status, message

    except Exception as e:
        custome_status = "Error"
        message = str(e)
        return custome_status, message




@login_required
@transaction.atomic
def void_cart(request):
    try:
        user_id = request.user.id
        single_or_all = "All"
        custome_status, message = remove_item_from_cart(single_or_all, user_id)
        return JsonResponse({"custome_status": custome_status, "message": message})
       
    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})




# # pos/views.py - Complete working check_out function

# import logging
# from datetime import datetime
# from decimal import Decimal
# from django.db import transaction as db_transaction
# from django.http import JsonResponse

# from fiscalisation.models import FiscalisationSettings
# # from fiscalisation.services import FiscalisationService
# from fiscalisation.services import create_fiscal_receipt, sync_receipt

# logger = logging.getLogger(__name__)


# @db_transaction.atomic
# def check_out(request):
#     try:
#         # ============================================================
#         # STEP 1: Check if fiscalisation is active and other conditions thats bypass fiscalisation
#         # ============================================================
#         fiscal_settings = FiscalisationSettings.get_settings()
#         fiscalisation_active = fiscal_settings.is_fiscalisation_active()
#         if fiscalisation_active == False:
#             fiscalisation_bypase_reason = "Turned off"
#         essential = ReceiptPaymentEssential.objects.filter(user=request.user).first()

#         # ----------if there are 2 payment methods
#         payments = Payment.objects.filter(payment_for="RECEIPT",created_by=request.user,loose_status=True)
#         dominant_payment_method = payments.first().payment_method
#         if payments.count() > 1:
#             fiscalisation_active = False
#             fiscalisation_bypase_reason = "Multple payment methods used"
#         else:
#             # ----------currency not on the list
#             if payments.first().payment_method.shortcut not in fiscal_settings.allowed_currences:
#                 fiscalisation_active = False
#                 fiscalisation_bypase_reason = "Currency not listed by Zimra"

#         # ----------there is a discount
#         if essential.discount > 0:
#             fiscalisation_active = False
#             fiscalisation_bypase_reason = "There is a discount"

#         # ============================================================
#         # STEP 2: Get customer ID
#         # ============================================================
#         customer_id = request.GET.get('customer_id')

#         # ============================================================
#         # STEP 3: Validate cart
#         # ============================================================
#         cart_items = CartItem.objects.filter(user=request.user)
#         if not cart_items.exists():
#             return JsonResponse({
#                 "custome_status": "Error",
#                 "message": "Your cart is empty"
#             })

#         # ============================================================
#         # STEP 4: Get or create sale transaction
#         # ============================================================
#         sale_transactions = SaleTransaction.objects.filter(created_by=request.user, open_state=True)
        

#         if sale_transactions.exists():
#             sale_transaction = sale_transactions[0]
#             for trans in sale_transactions:
#                 if trans.recipt_number != sale_transaction.recipt_number:
#                     trans.open_state = False
#                     trans.save()
#         else:
#             new_sale_transaction = SaleTransaction()
#             new_sale_transaction.discount = essential.discount if essential else 0
#             new_sale_transaction.created_by = request.user

#             try:
#                 customer = CustomerAccount.objects.get(id=int(customer_id))
#                 new_sale_transaction.buyer_name = customer.company_name or "Walk In Customer"
#                 new_sale_transaction.buyer_tin = customer.tin_number
#                 new_sale_transaction.buyer_vat = customer.vat_number
#                 new_sale_transaction.buyer_address = customer.address
#                 new_sale_transaction.buyer_tel = customer.phone_number
#             except (CustomerAccount.DoesNotExist, ValueError, TypeError):
#                 new_sale_transaction.buyer_name = "Walk In Customer"

#             new_sale_transaction.save()
#             sale_transaction = new_sale_transaction

#         # ============================================================
#         # STEP 5: Process cart items and build receipt lines
#         # ============================================================
#         subtotal = 0
#         discount = essential.discount if essential else 0
#         receipt_lines_payload = []

#         nontaxible_sales_amt_total = 0
#         document_total = 0
        
#         zero_per_taxamt = 0
#         zero_perc_sales_amt_total = 0

#         tax_amt_15_perc = 0
#         tax_15_perc_sales_total = 0

#         invoice_number_to_credit_debit = 0
#         qr_url = ""


#         for cart_item in cart_items:
#             # Create sale record
#             new_sale = Sale()
#             new_sale.sale_transaction = sale_transaction
#             new_sale.buying_unit_price = cart_item.buying_unit_price
#             new_sale.stock = cart_item.stock
#             new_sale.selling_price = cart_item.unit_price * cart_item.quantity
#             new_sale.VAT = 0
#             new_sale.unit_price = cart_item.unit_price
#             new_sale.quantity = cart_item.quantity
#             new_sale.used_batches = cart_item.used_baches_data
#             new_sale.used_batch_quantities = cart_item.used_baches_quantities_data
#             new_sale.created_by = request.user
#             new_sale.save()

#             stock_quantity_notification(new_sale.stock.id)
#             subtotal += cart_item.quantity * cart_item.unit_price * dominant_payment_method.rate

#             document_total += subtotal

#             # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#             # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#             # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

#             # 2=Zero%, 3=Exempt, 514=5%, 515=15.5%
#             int_tax_code = 2

#             if cart_item.stock.product.vat_code:
#                 int_tax_code = cart_item.stock.product.vat_code.zimra_tax_id


#             if int_tax_code == 1:
#                 str_tax_code = "A"
#                 tax_percentage = 0
#                 # exampt
#                 nontaxible_sales_amt_total += subtotal

#             elif int_tax_code == 2:
#                 str_tax_code = "B"
#                 tax_percentage = 0
#                 # 0 percent
#                 zero_perc_sales_amt_total += subtotal

#             elif int_tax_code == 3:
#                 str_tax_code = "C"
#                 tax_percentage = 15
#                 # 15 percent
#                 tax_amt_15_perc += 15/100 * float(subtotal)
#                 tax_15_perc_sales_total = subtotal

#             elif int_tax_code == 4 or int_tax_code == 517:
#                 int_tax_code = 517
#                 str_tax_code = "D"
#                 tax_percentage = 15.5
#                 # 15.5 percent
#                 tax_amt_15_perc += 15/100 * float(subtotal)
#                 tax_15_perc_sales_total = subtotal


#             # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#             # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#             # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


#             # Get HS code (REQUIRED by Binary API)
#             hs_code = getattr(cart_item.stock.product.zimra_hs_code, 'product_code', None)
#             if not hs_code:
#                 hs_code = getattr(cart_item.stock.product, 'hs_code', '95069100')

#             payment_method = dominant_payment_method


#             receipt_lines_payload.append({
#                 "LineDescription": f"{ cart_item.stock.product.title } { cart_item.stock.product.details }",
#                 "UnitPrice": str(round(cart_item.unit_price * payment_method.rate, 2)),
#                 "Quantity": str(round(cart_item.quantity, 2)),
#                 "Total": str(round(cart_item.unit_price * cart_item.quantity * dominant_payment_method.rate, 2)),
#                 "IntTaxCode": int_tax_code,
#                 "StrTaxCode": str_tax_code,
#                 "TaxPercentage": str(round(tax_percentage, 2)),
#                 "receiptLineHSCode": hs_code,
#             })

#             cart_item.delete()

#         total_cost = subtotal - discount

#         # ============================================================
#         # STEP 6: Process payments
#         # ============================================================
        
        
#         payment_method = dominant_payment_method.zimra_money_type_text.upper()
#         currency = dominant_payment_method.shortcut.upper()
#         payment_amount = 0
#         payments_list = []

#         for payment in payments:
#             payment.payment_for_id = sale_transaction.recipt_number
#             payment.loose_status = False
#             payment.save()
            
#             # Get payment method name (must be one of: CASH, CARD, MOBILEWALLET, COUPON, CREDIT, BANK TRANSFER)
#             payment_amount += float(payment.amount_paid)
            
#             payments_list.append({
#                 "PaymentMethodName": payment.payment_method.zimra_money_type_text.upper(),
#                 "PaymentAmt": str(round(payment.amount_paid, 2)),
#             })

#         # Clear discount
#         if essential:
#             essential.discount = 0
#             essential.save()

#         # Close sale transaction
#         sale_transaction.open_state = False
#         sale_transaction.save()

#         # ============================================================
#         # STEP 7: Handle fiscalisation
#         # ============================================================
#         # If fiscalisation paused, print receipt without QR
#         if not fiscalisation_active:
#             locale_receipt_number = sale_transaction.recipt_number
#             fiscal_details = get_fiscal_details(locale_receipt_number)

#             custome_status, message = print_receipt(sale_transaction.recipt_number,  " ", fiscal_details)
#             print_receipt(sale_transaction.recipt_number,  "(COPY)", fiscal_details)
#             return JsonResponse({
#                 "custome_status": custome_status or "",
#                 "message": f"{message} <br> Fiscalisation is paused.({ fiscalisation_bypase_reason })"
                
#             })

#         # ============================================================
#         # STEP 8: Create fiscal receipt
#         # ============================================================
#         the_password = ""
#         role = ""
#         payment_lines = payments_list
#         line_items = receipt_lines_payload
#         doc_type = "FISCALINVOICE"
#         doc_currency = currency
#         my_yyy_mm_dd_date = sale_transaction.created_at.strftime('%Y-%m-%d')
#         my_24hr_time_format_with_seconds = sale_transaction.created_at.strftime('%H:%M:%S')
#         document_total = document_total
#         nontaxible_sales_amt_total = nontaxible_sales_amt_total
#         zero_per_taxamt = zero_per_taxamt
#         zero_perc_sales_amt_total = zero_perc_sales_amt_total
#         tax_amt_15_perc = tax_amt_15_perc
#         tax_15_perc_sales_total = tax_15_perc_sales_total
#         invoice_number_to_credit_debit = invoice_number_to_credit_debit
#         local_invoice_number_to_credit_debit = 0
        
#         buyer_register_name = sale_transaction.buyer_name or "Walk In Customer"
#         buyer_TIN = sale_transaction.buyer_tin or ""
#         VAT_number = sale_transaction.buyer_vat or "" 
#         phone_no = sale_transaction.buyer_tel or "" 
#         email = sale_transaction.buyer_email or "" 
#         local_receipt_number = sale_transaction.recipt_number
#         status = "PENDING"

#         fiscal_receipt = create_fiscal_receipt(
#             the_password,
#             role,
#             payment_lines,
#             line_items,
#             doc_type,
#             doc_currency,
#             my_yyy_mm_dd_date,
#             my_24hr_time_format_with_seconds,
#             document_total,
#             nontaxible_sales_amt_total,
#             zero_per_taxamt,
#             zero_perc_sales_amt_total,
#             tax_amt_15_perc,
#             tax_15_perc_sales_total,
#             invoice_number_to_credit_debit,
#             local_invoice_number_to_credit_debit,
#             buyer_register_name,
#             buyer_TIN,
#             VAT_number,
#             phone_no,
#             email,
#             local_receipt_number,
#             status)

    
#         # ============================================================
#         # STEP 9: Try immediate sync
#         # ============================================================

#         sync_success = sync_receipt(fiscal_receipt.id)

#         try:
#             sync_success = sync_receipt(fiscal_receipt.id)
#             if sync_success and fiscal_receipt.qr_code_url:
#                 qr_url = fiscal_receipt.qr_code_url
#                 logger.info(f"Receipt {sale_transaction.recipt_number} synced successfully")
#             else:
#                 logger.info(f"Receipt {sale_transaction.recipt_number} queued for background sync")
#         except Exception as e:
#             logger.warning(f"Immediate sync failed for {sale_transaction.recipt_number}: {e}")

#         # ============================================================
#         # STEP 10: Print receipt
#         # ============================================================

        
#         fiscal_details = get_fiscal_details(sale_transaction.recipt_number)
#         custome_status, message = print_receipt(sale_transaction.recipt_number, " ", fiscal_details)
#         print_receipt(sale_transaction.recipt_number, "(COPY)", fiscal_details)

#         # ============================================================
#         # STEP 11: Return response
#         # ============================================================
#         if custome_status == "":
#             return JsonResponse({
#                 "custome_status": "",
#                 "message": f"Transaction successful. Fiscal receipt #{fiscal_receipt.inv_number or 'pending'}",
#                 "qr_code": qr_url,
#                 "fiscal_receipt_id": fiscal_receipt.id,
#                 "fiscal_receipt_number": fiscal_receipt.inv_number,
#             })
#         else:
#             return JsonResponse({
#                 "custome_status": custome_status,
#                 "message": message
#             })

#     except Exception as e:
#         logger.exception("Checkout failed")
#         return JsonResponse({
#             "custome_status": "Error",
#             "message": str(e)
#         })


# @login_required
# @transaction.atomic
# def void_payment(request):
#     try:
#         # receipt_money_portions = ReceiptMoneyPortion.objects.filter(loose_status=True, created_by=request.user)
#         receipt_money_portions = Payment.objects.filter(payment_for="RECEIPT", loose_status=True, created_by=request.user)
#         for receipt_money_portion in receipt_money_portions:
#             receipt_money_portion.delete()

#         essentials = ReceiptPaymentEssential.objects.filter(user=request.user)
#         if essentials:
#             essential = essentials[0]
#             for i in essentials:
#                 if i == essential:
#                     essential.discount = 0
#                     essential.save()
#                 else:
#                     essential.delete()

            
#         return JsonResponse({"custome_status": "", "message":""})

#     except Exception as e:
#         return JsonResponse({"custome_status":"Error", "message":str(e)})


# pos/views.py - check_out (keeping your original working calculations)
import logging
from datetime import datetime
from decimal import Decimal
from django.db import transaction as db_transaction
from django.http import JsonResponse

from fiscalisation.models import FiscalisationSettings
# from fiscalisation.services import FiscalisationService
from fiscalisation.services import create_fiscal_receipt, sync_receipt
import os 
from print_out.models import Printer
from print_out.print_client import print_this_document

logger = logging.getLogger(__name__)

def check_out(request):
    NEW_PRINT = os.getenv("NEW_PRINT")
    if NEW_PRINT:
        return check_out_new(request)

    else:
        return check_out_old(request)


def check_out_new(request):
    try:
        # ============================================================
        # STEP 1: Check if fiscalisation is active
        # ============================================================
        fiscal_settings = FiscalisationSettings.get_settings()
        fiscalisation_active = fiscal_settings.is_fiscalisation_active()
        fiscalisation_bypass_reason = ""
        
        essential = ReceiptPaymentEssential.objects.filter(user=request.user).first()

        # ---------- Check payments
        payments = Payment.objects.filter(
            payment_for="RECEIPT",
            created_by=request.user,
            loose_status=True
        )
        
        if not payments.exists():
            return JsonResponse({
                "custome_status": "Error",
                "message": "No payment found"
            })
        
        dominant_payment_method = payments.first().payment_method
        
        # Currency check
        allowed_currencies = [c.strip().upper() for c in fiscal_settings.allowed_currences.split(',')]
        if dominant_payment_method.shortcut.upper() not in allowed_currencies:
            fiscalisation_active = False
            fiscalisation_bypass_reason = f"Currency '{dominant_payment_method.shortcut}' not allowed by ZIMRA"
        
        # Multiple payment methods in same currency - ALLOWED
        # Multiple currencies - NOT ALLOWED
        payment_currencies = set(p.payment_method.shortcut.upper() for p in payments)
        if len(payment_currencies) > 1:
            fiscalisation_active = False
            fiscalisation_bypass_reason = f"Multiple currencies not allowed: {', '.join(payment_currencies)}"
        
        # Discount check
        if essential and essential.discount > 0:
            fiscalisation_active = False
            fiscalisation_bypass_reason = "Discounts must be applied as negative line items for fiscalisation"

        # ============================================================
        # STEP 2: Get customer ID
        # ============================================================
        customer_id = request.GET.get('customer_id')

        # ============================================================
        # STEP 3: Validate cart
        # ============================================================
        cart_items = CartItem.objects.filter(user=request.user)
        if not cart_items.exists():
            return JsonResponse({
                "custome_status": "Error",
                "message": "Your cart is empty"
            })

        # ============================================================
        # STEP 4: Get or create sale transaction
        # ============================================================
        sale_transactions = SaleTransaction.objects.filter(
            created_by=request.user, 
            open_state=True
        )
        
        if sale_transactions.exists():
            sale_transaction = sale_transactions[0]
            for trans in sale_transactions:
                if trans.recipt_number != sale_transaction.recipt_number:
                    trans.open_state = False
                    trans.save()
        else:
            new_sale_transaction = SaleTransaction()
            new_sale_transaction.discount = essential.discount if essential else 0
            new_sale_transaction.created_by = request.user

            try:
                customer = CustomerAccount.objects.get(id=int(customer_id))
                new_sale_transaction.buyer_name = customer.company_name or "Walk In Customer"
                new_sale_transaction.buyer_tin = customer.tin_number or ""
                new_sale_transaction.buyer_vat = customer.vat_number or ""
                new_sale_transaction.buyer_address = customer.address or ""
                new_sale_transaction.buyer_tel = customer.phone_number or ""
                new_sale_transaction.buyer_email = customer.email or ""
            except (CustomerAccount.DoesNotExist, ValueError, TypeError):
                new_sale_transaction.buyer_name = "Walk In Customer"

            new_sale_transaction.save()
            sale_transaction = new_sale_transaction

        # ============================================================
        # STEP 5: Process cart items and build receipt lines
        # ============================================================
        subtotal = Decimal('0')
        discount = essential.discount if essential else Decimal('0')
        receipt_lines_payload = []

        # Tax accumulators
        nontaxible_sales_amt_total = Decimal('0')
        document_total = Decimal('0')
        zero_per_taxamt = Decimal('0')
        zero_perc_sales_amt_total = Decimal('0')
        tax_amt_15_perc = Decimal('0')
        tax_15_perc_sales_total = Decimal('0')
        invoice_number_to_credit_debit = Decimal('0')
        qr_url = ""

        for cart_item in cart_items:
            # Create sale record
            new_sale = Sale()
            new_sale.sale_transaction = sale_transaction
            new_sale.buying_unit_price = cart_item.buying_unit_price
            new_sale.stock = cart_item.stock
            new_sale.selling_price = cart_item.unit_price * cart_item.quantity
            new_sale.VAT = 0
            new_sale.unit_price = cart_item.unit_price
            new_sale.quantity = cart_item.quantity
            new_sale.used_batches = cart_item.used_baches_data
            new_sale.used_batch_quantities = cart_item.used_baches_quantities_data
            new_sale.created_by = request.user
            new_sale.save()

            try:
                stock_quantity_notification(new_sale.stock.id)
            except:
                pass

            # Calculate subtotal
            item_total = cart_item.quantity * cart_item.unit_price * dominant_payment_method.rate
            subtotal += item_total
            document_total += item_total

            # Determine tax code
            int_tax_code = 2  # Default Zero%
            tax_percentage = 0
            
            if cart_item.stock.product.vat_code:
                int_tax_code = cart_item.stock.product.vat_code.zimra_tax_id or 2
            
            
            if int_tax_code == 1:  # Exempt
                str_tax_code = "A"
                tax_percentage = ""
                nontaxible_sales_amt_total += item_total

            elif int_tax_code == 2:  # Zero %
                str_tax_code = "B"
                tax_percentage = str(round(0, 2))
                zero_perc_sales_amt_total += item_total

            elif int_tax_code == 3:  # 15% VAT Inclusive
                str_tax_code = "C"
                tax_percentage = str(round(15, 2))
                # CORRECT: Tax = Total × (15 / 115)
                tax_amt_15_perc += Decimal(str(15 / 115)) * Decimal(str(item_total))
                tax_15_perc_sales_total += item_total

            elif int_tax_code == 4 or int_tax_code == 517:  # 15.5% VAT Inclusive
                int_tax_code = 517
                str_tax_code = "D"
                tax_percentage = str(round(15.5, 2))
                # CORRECT: Tax = Total × (15.5 / 115.5)
                tax_amt_15_perc += Decimal(str(15.5 / 115.5)) * Decimal(str(item_total))
                tax_15_perc_sales_total += item_total

            else:
                str_tax_code = "B"
                tax_percentage = str(round(0, 2))
                zero_perc_sales_amt_total += item_total

            # Get HS code
            hs_code = cart_item.stock.product.zimra_hs_code
            if not is_correct_hs_code_format(str(hs_code)):
                hs_code = cart_item.stock.product.vat_code.default_hs_code
                if not is_correct_hs_code_format(str(hs_code)):
                    hs_code = '95069100'


            payment_method = dominant_payment_method

            receipt_lines_payload.append({
                "LineDescription": f"{cart_item.stock.product.title} {cart_item.stock.product.details}",
                "UnitPrice": str(round(cart_item.unit_price * payment_method.rate, 2)),
                "Quantity": str(round(cart_item.quantity, 2)),
                "Total": str(round(cart_item.unit_price * cart_item.quantity * dominant_payment_method.rate, 2)),
                "IntTaxCode": int_tax_code,
                "StrTaxCode": str_tax_code,
                "TaxPercentage": tax_percentage,
                "receiptLineHSCode": hs_code,
            })

            cart_item.delete()

        # Calculate total after discount
        total_cost = subtotal - discount

        # ============================================================
        # STEP 6: Process payments
        # ============================================================
        payment_method = dominant_payment_method.zimra_money_type_text.upper()
        currency = dominant_payment_method.shortcut.upper()
        payment_amount = 0
        payments_list = []

        for payment in payments:
            payment.payment_for_id = sale_transaction.recipt_number
            payment.loose_status = False
            payment.save()
            
            payment_amount += Decimal(str(payment.amount_paid))
            
            payments_list.append({
                "PaymentMethodName": payment.payment_method.zimra_money_type_text.upper(),
                "PaymentAmt": str(round(payment.amount_paid, 2)),
            })

        # Clear discount
        if essential:
            essential.discount = 0
            essential.save()

        # Close sale transaction
        sale_transaction.open_state = False
        sale_transaction.save()

        # ============================================================
        # STEP 7: Handle fiscalisation
        # ============================================================

        if fiscalisation_active:
            locale_receipt_number = sale_transaction.recipt_number
            # fiscal_details = get_fiscal_details(locale_receipt_number)


            # custome_status, message = print_receipt(sale_transaction.recipt_number, " ", fiscal_details)
            # print_receipt(sale_transaction.recipt_number, "(COPY)", fiscal_details)
            # print_this_document(request, printer, "RECEIPT", sale_transaction.recipt_number, "(COPY)")


            # return JsonResponse({
            #     "custome_status": custome_status or "",
            #     "message": f"{message} <br> Fiscalisation is paused.({fiscalisation_bypass_reason})"
            # })

            # ============================================================
            # STEP 8: Create fiscal receipt
            # ============================================================
            the_password = ""
            role = ""
            payment_lines = payments_list
            line_items = receipt_lines_payload
            doc_type = "FISCALINVOICE"
            doc_currency = currency
            my_yyy_mm_dd_date = sale_transaction.created_at.strftime('%Y-%m-%d')
            my_24hr_time_format_with_seconds = sale_transaction.created_at.strftime('%H:%M:%S')
            document_total = document_total
            nontaxible_sales_amt_total = nontaxible_sales_amt_total
            zero_per_taxamt = zero_per_taxamt
            zero_perc_sales_amt_total = zero_perc_sales_amt_total
            tax_amt_15_perc = tax_amt_15_perc
            tax_15_perc_sales_total = tax_15_perc_sales_total
            invoice_number_to_credit_debit = invoice_number_to_credit_debit
            local_invoice_number_to_credit_debit = 0
            
            buyer_register_name = sale_transaction.buyer_name or "Walk In Customer"
            buyer_TIN = sale_transaction.buyer_tin or ""
            VAT_number = sale_transaction.buyer_vat or "" 
            phone_no = sale_transaction.buyer_tel or "" 
            email = sale_transaction.buyer_email or "" 
            local_receipt_number = sale_transaction.recipt_number
            status = "PENDING"

            fiscal_receipt = create_fiscal_receipt(
                the_password,
                role,
                payment_lines,
                line_items,
                doc_type,
                doc_currency,
                my_yyy_mm_dd_date,
                my_24hr_time_format_with_seconds,
                document_total,
                nontaxible_sales_amt_total,
                zero_per_taxamt,
                zero_perc_sales_amt_total,
                tax_amt_15_perc,
                tax_15_perc_sales_total,
                invoice_number_to_credit_debit,
                local_invoice_number_to_credit_debit,
                buyer_register_name,
                buyer_TIN,
                VAT_number,
                phone_no,
                email,
                local_receipt_number,
                status
            )


            # ============================================================
            # STEP 9: Start background sync (NON-BLOCKING)
            # ============================================================
            from fiscalisation.services import sync_receipt_async
            
            # Start sync in background - doesn't block checkout
            sync_receipt_async(fiscal_receipt.id)

            time.sleep(5)

            
            logger.info(f"Receipt {sale_transaction.recipt_number} queued for background sync")

        # ============================================================
        # STEP 10: Print receipt
        # ============================================================
        
        # fiscal_details = get_fiscal_details(sale_transaction.recipt_number)
        # custome_status, message = print_receipt(sale_transaction.recipt_number, " ", fiscal_details)
        # print_receipt(sale_transaction.recipt_number, "(COPY)", fiscal_details)

        # ============================================================
        # STEP 11: Return response
        # ============================================================
        # if custome_status == "":
        #     return JsonResponse({
        #         "custome_status": "",
        #         "message": f"Transaction successful. Fiscal receipt #{fiscal_receipt.inv_number or 'pending'}",
        #         "qr_code": fiscal_receipt.qr_code_url or "",
        #         "fiscal_receipt_id": fiscal_receipt.id,
        #         "fiscal_receipt_number": fiscal_receipt.inv_number,
        #     })
        # else:


        printer = Printer.objects.get(id=1)  # or by name

        print_this_document(request, printer, "RECEIPT", sale_transaction.recipt_number, "(COPY)")
        return JsonResponse({
            "custome_status": "",
            "message": "Done"
        })



    except Exception as e:
        logger.exception("Checkout failed")
        return JsonResponse({
            "custome_status": "Error",
            "message": str(e)
        })

@transaction.atomic
def check_out_old(request):
    try:
        # ============================================================
        # STEP 1: Check if fiscalisation is active
        # ============================================================
        fiscal_settings = FiscalisationSettings.get_settings()
        fiscalisation_active = fiscal_settings.is_fiscalisation_active()
        fiscalisation_bypass_reason = ""
        
        essential = ReceiptPaymentEssential.objects.filter(user=request.user).first()

        # ---------- Check payments
        payments = Payment.objects.filter(
            payment_for="RECEIPT",
            created_by=request.user,
            loose_status=True
        )
        
        if not payments.exists():
            return JsonResponse({
                "custome_status": "Error",
                "message": "No payment found"
            })
        
        dominant_payment_method = payments.first().payment_method
        
        # Currency check
        allowed_currencies = [c.strip().upper() for c in fiscal_settings.allowed_currences.split(',')]
        if dominant_payment_method.shortcut.upper() not in allowed_currencies:
            fiscalisation_active = False
            fiscalisation_bypass_reason = f"Currency '{dominant_payment_method.shortcut}' not allowed by ZIMRA"
        
        # Multiple payment methods in same currency - ALLOWED
        # Multiple currencies - NOT ALLOWED
        payment_currencies = set(p.payment_method.shortcut.upper() for p in payments)
        if len(payment_currencies) > 1:
            fiscalisation_active = False
            fiscalisation_bypass_reason = f"Multiple currencies not allowed: {', '.join(payment_currencies)}"
        
        # Discount check
        if essential and essential.discount > 0:
            fiscalisation_active = False
            fiscalisation_bypass_reason = "Discounts must be applied as negative line items for fiscalisation"

        # ============================================================
        # STEP 2: Get customer ID
        # ============================================================
        customer_id = request.GET.get('customer_id')

        # ============================================================
        # STEP 3: Validate cart
        # ============================================================
        cart_items = CartItem.objects.filter(user=request.user)
        if not cart_items.exists():
            return JsonResponse({
                "custome_status": "Error",
                "message": "Your cart is empty"
            })

        # ============================================================
        # STEP 4: Get or create sale transaction
        # ============================================================
        sale_transactions = SaleTransaction.objects.filter(
            created_by=request.user, 
            open_state=True
        )
        
        if sale_transactions.exists():
            sale_transaction = sale_transactions[0]
            for trans in sale_transactions:
                if trans.recipt_number != sale_transaction.recipt_number:
                    trans.open_state = False
                    trans.save()
        else:
            new_sale_transaction = SaleTransaction()
            new_sale_transaction.discount = essential.discount if essential else 0
            new_sale_transaction.created_by = request.user

            try:
                customer = CustomerAccount.objects.get(id=int(customer_id))
                new_sale_transaction.buyer_name = customer.company_name or "Walk In Customer"
                new_sale_transaction.buyer_tin = customer.tin_number or ""
                new_sale_transaction.buyer_vat = customer.vat_number or ""
                new_sale_transaction.buyer_address = customer.address or ""
                new_sale_transaction.buyer_tel = customer.phone_number or ""
                new_sale_transaction.buyer_email = customer.email or ""
            except (CustomerAccount.DoesNotExist, ValueError, TypeError):
                new_sale_transaction.buyer_name = "Walk In Customer"

            new_sale_transaction.save()
            sale_transaction = new_sale_transaction

        # ============================================================
        # STEP 5: Process cart items and build receipt lines
        # ============================================================
        subtotal = Decimal('0')
        discount = essential.discount if essential else Decimal('0')
        receipt_lines_payload = []

        # Tax accumulators
        nontaxible_sales_amt_total = Decimal('0')
        document_total = Decimal('0')
        zero_per_taxamt = Decimal('0')
        zero_perc_sales_amt_total = Decimal('0')
        tax_amt_15_perc = Decimal('0')
        tax_15_perc_sales_total = Decimal('0')
        invoice_number_to_credit_debit = Decimal('0')
        qr_url = ""

        for cart_item in cart_items:
            # Create sale record
            new_sale = Sale()
            new_sale.sale_transaction = sale_transaction
            new_sale.buying_unit_price = cart_item.buying_unit_price
            new_sale.stock = cart_item.stock
            new_sale.selling_price = cart_item.unit_price * cart_item.quantity
            new_sale.VAT = 0
            new_sale.unit_price = cart_item.unit_price
            new_sale.quantity = cart_item.quantity
            new_sale.used_batches = cart_item.used_baches_data
            new_sale.used_batch_quantities = cart_item.used_baches_quantities_data
            new_sale.created_by = request.user
            new_sale.save()

            try:
                stock_quantity_notification(new_sale.stock.id)
            except:
                pass

            # Calculate subtotal
            item_total = cart_item.quantity * cart_item.unit_price * dominant_payment_method.rate
            subtotal += item_total
            document_total += item_total

            # Determine tax code
            int_tax_code = 2  # Default Zero%
            tax_percentage = 0
            
            if cart_item.stock.product.vat_code:
                int_tax_code = cart_item.stock.product.vat_code.zimra_tax_id or 2
            
            
            if int_tax_code == 1:  # Exempt
                str_tax_code = "A"
                tax_percentage = ""
                nontaxible_sales_amt_total += item_total

            elif int_tax_code == 2:  # Zero %
                str_tax_code = "B"
                tax_percentage = str(round(0, 2))
                zero_perc_sales_amt_total += item_total

            elif int_tax_code == 3:  # 15% VAT Inclusive
                str_tax_code = "C"
                tax_percentage = str(round(15, 2))
                # CORRECT: Tax = Total × (15 / 115)
                tax_amt_15_perc += Decimal(str(15 / 115)) * Decimal(str(item_total))
                tax_15_perc_sales_total += item_total

            elif int_tax_code == 4 or int_tax_code == 517:  # 15.5% VAT Inclusive
                int_tax_code = 517
                str_tax_code = "D"
                tax_percentage = str(round(15.5, 2))
                # CORRECT: Tax = Total × (15.5 / 115.5)
                tax_amt_15_perc += Decimal(str(15.5 / 115.5)) * Decimal(str(item_total))
                tax_15_perc_sales_total += item_total

            else:
                str_tax_code = "B"
                tax_percentage = str(round(0, 2))
                zero_perc_sales_amt_total += item_total

            # Get HS code
            hs_code = cart_item.stock.product.zimra_hs_code
            if not is_correct_hs_code_format(str(hs_code)):
                hs_code = cart_item.stock.product.vat_code.default_hs_code
                if not is_correct_hs_code_format(str(hs_code)):
                    hs_code = '95069100'


            payment_method = dominant_payment_method

            receipt_lines_payload.append({
                "LineDescription": f"{cart_item.stock.product.title} {cart_item.stock.product.details}",
                "UnitPrice": str(round(cart_item.unit_price * payment_method.rate, 2)),
                "Quantity": str(round(cart_item.quantity, 2)),
                "Total": str(round(cart_item.unit_price * cart_item.quantity * dominant_payment_method.rate, 2)),
                "IntTaxCode": int_tax_code,
                "StrTaxCode": str_tax_code,
                "TaxPercentage": tax_percentage,
                "receiptLineHSCode": hs_code,
            })

            cart_item.delete()

        # Calculate total after discount
        total_cost = subtotal - discount

        # ============================================================
        # STEP 6: Process payments
        # ============================================================
        payment_method = dominant_payment_method.zimra_money_type_text.upper()
        currency = dominant_payment_method.shortcut.upper()
        payment_amount = 0
        payments_list = []

        for payment in payments:
            payment.payment_for_id = sale_transaction.recipt_number
            payment.loose_status = False
            payment.save()
            
            payment_amount += Decimal(str(payment.amount_paid))
            
            payments_list.append({
                "PaymentMethodName": payment.payment_method.zimra_money_type_text.upper(),
                "PaymentAmt": str(round(payment.amount_paid, 2)),
            })

        # Clear discount
        if essential:
            essential.discount = 0
            essential.save()

        # Close sale transaction
        sale_transaction.open_state = False
        sale_transaction.save()

        # ============================================================
        # STEP 7: Handle fiscalisation
        # ============================================================
        if not fiscalisation_active:
            locale_receipt_number = sale_transaction.recipt_number
            fiscal_details = get_fiscal_details(locale_receipt_number)

            custome_status, message = print_receipt(sale_transaction.recipt_number, " ", fiscal_details)
            print_receipt(sale_transaction.recipt_number, "(COPY)", fiscal_details)
            return JsonResponse({
                "custome_status": custome_status or "",
                "message": f"{message} <br> Fiscalisation is paused.({fiscalisation_bypass_reason})"
            })

        # ============================================================
        # STEP 8: Create fiscal receipt
        # ============================================================
        the_password = ""
        role = ""
        payment_lines = payments_list
        line_items = receipt_lines_payload
        doc_type = "FISCALINVOICE"
        doc_currency = currency
        my_yyy_mm_dd_date = sale_transaction.created_at.strftime('%Y-%m-%d')
        my_24hr_time_format_with_seconds = sale_transaction.created_at.strftime('%H:%M:%S')
        document_total = document_total
        nontaxible_sales_amt_total = nontaxible_sales_amt_total
        zero_per_taxamt = zero_per_taxamt
        zero_perc_sales_amt_total = zero_perc_sales_amt_total
        tax_amt_15_perc = tax_amt_15_perc
        tax_15_perc_sales_total = tax_15_perc_sales_total
        invoice_number_to_credit_debit = invoice_number_to_credit_debit
        local_invoice_number_to_credit_debit = 0
        
        buyer_register_name = sale_transaction.buyer_name or "Walk In Customer"
        buyer_TIN = sale_transaction.buyer_tin or ""
        VAT_number = sale_transaction.buyer_vat or "" 
        phone_no = sale_transaction.buyer_tel or "" 
        email = sale_transaction.buyer_email or "" 
        local_receipt_number = sale_transaction.recipt_number
        status = "PENDING"

        fiscal_receipt = create_fiscal_receipt(
            the_password,
            role,
            payment_lines,
            line_items,
            doc_type,
            doc_currency,
            my_yyy_mm_dd_date,
            my_24hr_time_format_with_seconds,
            document_total,
            nontaxible_sales_amt_total,
            zero_per_taxamt,
            zero_perc_sales_amt_total,
            tax_amt_15_perc,
            tax_15_perc_sales_total,
            invoice_number_to_credit_debit,
            local_invoice_number_to_credit_debit,
            buyer_register_name,
            buyer_TIN,
            VAT_number,
            phone_no,
            email,
            local_receipt_number,
            status
        )

        # ============================================================
        # STEP 9: Start background sync (NON-BLOCKING)
        # ============================================================
        from fiscalisation.services import sync_receipt_async
        
        # Start sync in background - doesn't block checkout
        sync_receipt_async(fiscal_receipt.id)
        
        logger.info(f"Receipt {sale_transaction.recipt_number} queued for background sync")

        # ============================================================
        # STEP 10: Print receipt
        # ============================================================
        fiscal_details = get_fiscal_details(sale_transaction.recipt_number)
        custome_status, message = print_receipt(sale_transaction.recipt_number, " ", fiscal_details)
        print_receipt(sale_transaction.recipt_number, "(COPY)", fiscal_details)

        # ============================================================
        # STEP 11: Return response
        # ============================================================
        if custome_status == "":
            return JsonResponse({
                "custome_status": "",
                "message": f"Transaction successful. Fiscal receipt #{fiscal_receipt.inv_number or 'pending'}",
                "qr_code": fiscal_receipt.qr_code_url or "",
                "fiscal_receipt_id": fiscal_receipt.id,
                "fiscal_receipt_number": fiscal_receipt.inv_number,
            })
        else:
            return JsonResponse({
                "custome_status": custome_status,
                "message": message
            })

    except Exception as e:
        logger.exception("Checkout failed")
        return JsonResponse({
            "custome_status": "Error",
            "message": str(e)
        })



@login_required
@transaction.atomic
def void_payment(request):
    try:
        # receipt_money_portions = ReceiptMoneyPortion.objects.filter(loose_status=True, created_by=request.user)
        receipt_money_portions = Payment.objects.filter(payment_for="RECEIPT", loose_status=True, created_by=request.user)
        for receipt_money_portion in receipt_money_portions:
            receipt_money_portion.delete()

        essentials = ReceiptPaymentEssential.objects.filter(user=request.user)
        if essentials:
            essential = essentials[0]
            for i in essentials:
                if i == essential:
                    essential.discount = 0
                    essential.save()
                else:
                    essential.delete()

            
        return JsonResponse({"custome_status": "", "message":""})

    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})



@login_required
def load_receipt_payment_portions_data(request):
    # receipt_money_portions = ReceiptMoneyPortion.objects.filter(loose_status=True, created_by=request.user)
    receipt_money_portions = Payment.objects.filter(payment_for="RECEIPT", loose_status=True, created_by=request.user)


    # getting the required amounts
    # ---------------------------------------------------------------------------------------------------------------------
    cart_items = CartItem.objects.filter(user=request.user)
    subtotal = 0
    VAT = 0
    for cart_item in cart_items:
        subtotal += cart_item.quantity * cart_item.unit_price
        VAT += (cart_item.stock.product.vat_code.percentage/100) * (cart_item.quantity * cart_item.unit_price)

    total_price = subtotal #+ VAT
    # ---------------------------------------------------------------------------------------------------------------------


    discount = 0
    paid_value = 0
    change_or_remaining_value = 0
    change_or_remaining_text = ""
    receipt_money_portions_table_rows = []
    row = []


    for receipt_money_portion in receipt_money_portions:
        rated_amount = float(receipt_money_portion.amount_paid) / float(receipt_money_portion.rate)
        row = [
            f"{receipt_money_portion.payment_method.shortcut}",
            f"{receipt_money_portion.amount_paid}",
            f"{ locale.format_string('%.4f', receipt_money_portion.rate, grouping=True)}",
            f"{ locale.format_string('%.2f', rated_amount, grouping=True)}"
        ]
        receipt_money_portions_table_rows.append(row)
        paid_value += rated_amount
   

    essentials = ReceiptPaymentEssential.objects.filter(user=request.user)
    if essentials:
        discount = essentials[0].discount


    change_or_remaining_value = float(total_price) - float(paid_value) - float(discount)
    if change_or_remaining_value < 0:
        change_or_remaining_text = "CHANGE"
    else:
        change_or_remaining_text = "REQUIRED"


    



    totals = {
        "total_receipt_price": locale.format_string('%.2f', float(total_price), grouping=True),
        "discount": locale.format_string('%.2f', float(discount), grouping=True),
        "paid_value": locale.format_string('%.2f',  float(paid_value), grouping=True),
        "change_or_remaining_text": change_or_remaining_text,
        "change_or_remaining_value": locale.format_string('%.2f',  float(change_or_remaining_value), grouping=True)
    }

    return JsonResponse({"receipt_money_portions_table_rows": receipt_money_portions_table_rows, "totals":totals})


@login_required
def reprint_user_last_receipt(request):
    sale_transaction = SaleTransaction.objects.filter(created_by=request.user).last()
    if sale_transaction:
        locale_receipt_number = sale_transaction.recipt_number
        fiscal_details = get_fiscal_details(locale_receipt_number)
        custome_status, message = print_receipt(sale_transaction.recipt_number, " ", fiscal_details)
        print_receipt(sale_transaction.recipt_number, "(COPY)", fiscal_details)
        return JsonResponse({"custome_status":custome_status, "message":message})
    else:
        return JsonResponse({"custome_status":"Error", "message":"No receipt found for this user."})




@login_required
def load_cart_data(request):
    cart_items = CartItem.objects.filter(user=request.user)
    # formarting numbers
    
    
    VAT = 0
    subtotal = 0
    total_price = 0


    cart_items_table_rows = []
    row = []
    for cart_item in cart_items:
        row = [
            f"({ cart_item.stock.product.product_code }) { cart_item.stock.product.title } { cart_item.stock.product.details }",
            f"{ locale.format_string('%.2f', cart_item.unit_price, grouping=True)}",
            f"{ locale.format_string('%.0f', cart_item.quantity, grouping=True)}",
            f"{ locale.format_string('%.2f', cart_item.quantity * cart_item.unit_price, grouping=True)}",
            f"{ cart_item.id }",
            f"{ cart_item.stock.total_units }",
        ]
        cart_items_table_rows.append(row)


        subtotal += cart_item.quantity * cart_item.unit_price

        VAT += (cart_item.stock.product.vat_code.percentage/100) * (cart_item.quantity * cart_item.unit_price)

    total_price = subtotal #+ VAT


    totals = {
        "subtotal_value":locale.format_string('%.2f', subtotal, grouping=True),
        "VAT_value": locale.format_string('%.2f', VAT, grouping=True),
        "total_price_value": locale.format_string('%.2f', total_price, grouping=True),
    }


    
    return JsonResponse({"cart_items_table_rows": cart_items_table_rows, "totals":totals})




@login_required
@transaction.atomic
def add_stock_to_cart(request):
    try:
        try:
            stock_id = int(request.GET.get('stock_id'))
            quantity = int(request.GET.get('quantity'))
        except Exception as e:
            message = e
            print(f"Error {e}")
            return JsonResponse({"custome_status":"Error", "message":message})

        stock = Stock.objects.get(id=stock_id)


        # creating a cart item
        #   check if the same stock exist
        stock_cart_item_already_exist = CartItem.objects.filter(stock=stock, user=request.user)
        if stock_cart_item_already_exist:
            old_item = stock_cart_item_already_exist[0]
            current_cart_item = old_item

            current_cart_item.unit_price = float(stock.selling_price)
            current_cart_item.quantity = float(current_cart_item.quantity) + float(quantity)
            current_cart_item.VAT = float(stock.selling_price * stock.product.vat_code.percentage/100) * quantity

        else:
            new_cart_item = CartItem()
            new_cart_item.stock = stock
            new_cart_item.unit_price = stock.selling_price
            new_cart_item.quantity = quantity
            new_cart_item.VAT = (stock.selling_price * stock.product.vat_code.percentage/100) * quantity
            new_cart_item.buying_unit_price = stock.avarage_unit_cost
            new_cart_item.user = request.user
            new_cart_item.used_baches_data = ""
            new_cart_item.used_baches_quantities_data = ""
            # new_cart_item.save()

            current_cart_item = new_cart_item

        
        batch_ids = []

        #collecting all batch ids that can be used
        available_for_sale_batches = Batch.objects.filter(status=True, stock=stock, total_units__gte=0)
        for batch in available_for_sale_batches:
            batch_ids.append(batch.id)

        requared_quntity = quantity
        #check if there are enogh products
        total_units_available_for_sale = 0
        for batch in available_for_sale_batches:
            total_units_available_for_sale += batch.total_units

        if total_units_available_for_sale >= requared_quntity:
            print(f"available enough......................... {total_units_available_for_sale}")
            #altering batches quntities and deactivating empty ones
            actively_requred_quantity = requared_quntity
            still_needed = True
            for batch in available_for_sale_batches:
                if still_needed:
                    pass
                else:
                    break

                if batch.total_units - actively_requred_quantity >= 0:
                    batch.total_units = batch.total_units - actively_requred_quantity
                    batch.save()
                    still_needed = False
                    current_cart_item.used_baches_data += f"{batch.id},"
                    current_cart_item.used_baches_quantities_data += f"{actively_requred_quantity},"
                else:
                    actively_requred_quantity -= batch.total_units
                    available_in_batch = batch.total_units
                    batch.total_units = 0
                    # batch.status = False
                    batch.save()
                    current_cart_item.used_baches_data += f"{batch.id},"
                    current_cart_item.used_baches_quantities_data += f"{available_in_batch},"

            current_cart_item.save()

            message = "Added succesfully"
            return JsonResponse({"custome_status":"", "message":message})


        else:
            print(f"available not enough -------------------------------------{total_units_available_for_sale}")

            message = (f"Not enough products in stock. Available units for this item: {total_units_available_for_sale}")


        



        return JsonResponse({"custome_status":"Error", "message":message})

    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})



# --------------------------------------------------------------------
# //AJAX
# --------------------------------------------------------------------




