from decimal import Decimal

from django.views.decorators.csrf import csrf_exempt

from django.shortcuts import render, redirect

from rest_framework import viewsets

from django.contrib.auth.decorators import login_required


from django.http import HttpResponse, HttpResponseRedirect, JsonResponse



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

from order.views import days_from_now_python



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




import time
import logging
from datetime import datetime, timedelta

from django.db import transaction as db_transaction
from django.http import JsonResponse
from fiscalisation.models import FiscalDevice, FiscalState, FiscalReceipt, FiscalSettings
from fiscalisation.services import zimra_now, validate_receipt_for_zimra
from fiscalisation.views import device, classify_submit_response
import json

logger = logging.getLogger(__name__)

@db_transaction.atomic
def check_out(request):
    try:
        # If a CSO has paused fiscalisation (because ZIMRA is down, cert
        # expired, etc.), the till keeps trading: we still create the
        # Sale/Payment records, but skip all ZIMRA signing/submission and
        # print without a QR. The reseller is then on the hook to issue
        # manual paper receipts for the audit trail (and to resume
        # fiscalisation as soon as possible).
        fiscal_settings = FiscalSettings.get()
        fiscalization_paused = fiscal_settings.fiscalization_paused

        fiscal_device = None
        fiscal_state = None
        if not fiscalization_paused:
            try:
                fiscal_device = FiscalDevice.objects.get(is_active=True)
                # select_for_update so two concurrent checkouts can't both
                # read receipt_global_no=N and both write N+1.
                fiscal_state = (
                    FiscalState.objects
                    .select_for_update()
                    .get(device=fiscal_device)
                )
            except (FiscalDevice.DoesNotExist, FiscalState.DoesNotExist):
                return JsonResponse({
                    "custome_status": "Error",
                    "message": (
                        "Fiscal Device or State Configuration is missing. "
                        "Either add a device at /fiscalisation/devices/ or "
                        "pause fiscalisation to keep trading."
                    ),
                })

            if not fiscal_state.is_day_open:
                return JsonResponse({
                    "custome_status": "Error",
                    "message": "Fiscal Day is closed. Please open the business day before checking out (or pause fiscalisation to bypass)."
                })

        customer_id = request.GET.get('customer_id')

        cart_items = CartItem.objects.filter(user=request.user)
        if cart_items:
            pass
        else:
            return JsonResponse({"custome_status": "Error", "message":"You cart is empty"})
        
        # Creating a sale transaction
        sale_transactions = SaleTransaction.objects.filter(created_by=request.user, open_state=True)
        essential = ReceiptPaymentEssential.objects.filter(user=request.user)[0]
        if sale_transactions:
            sale_transaction = sale_transactions[0]
            for i in sale_transactions:
                if i.recipt_number != sale_transaction.recipt_number:
                    i.open_state = False
                    i.save()
        else:
            new_sale_transaction = SaleTransaction()
            new_sale_transaction.discount = essential.discount
            new_sale_transaction.created_by = request.user

            try:
                customer = CustomerAccount.objects.get(id=int(customer_id))
                new_sale_transaction.buyer_name = customer.company_name
                new_sale_transaction.buyer_tin = customer.tin_number
                new_sale_transaction.buyer_vat = customer.vat_number
                new_sale_transaction.buyer_address = customer.address
                new_sale_transaction.buyer_tel = customer.phone_number
            except:
                pass

            new_sale_transaction.save()
            sale_transaction = new_sale_transaction

        # ---------------------------------------------------------
        # Compile Cart Items into Sales & Construct ZIMRA Payload Lines
        # ---------------------------------------------------------
        subtotal = 0
        try:
            discount = essential.discount
        except:
            discount = 0

        receipt_lines_payload = []
        
        for index, cart_item in enumerate(cart_items, start=1):
            new_sale = Sale()
            new_sale.sale_transaction = sale_transaction
            new_sale.buying_unit_price = cart_item.buying_unit_price
            new_sale.stock = cart_item.stock
            new_sale.selling_price = cart_item.unit_price * cart_item.quantity
            new_sale.VAT = 0 # Tax inclusive setup: Ignored and forced cleanly to 0
            new_sale.unit_price = cart_item.unit_price
            new_sale.quantity = cart_item.quantity
            new_sale.used_batches = cart_item.used_baches_data
            new_sale.used_batch_quantities = cart_item.used_baches_quantities_data
            new_sale.created_by = request.user

            new_sale.save()
            stock_quantity_notification(new_sale.stock.id)
            cart_item.delete()

            # Accumulate subtotal using the inclusive customer price
            subtotal += cart_item.quantity * cart_item.unit_price

            tax_percentage = cart_item.stock.product.vat_code.percentage

            # Build lines dictionary in the format prepareReceipt expects.
            # prepareReceipt computes taxID internally from tax_percent via applicableTaxes.
            receipt_lines_payload.append({
                "item_name": cart_item.stock.product.title,
                "unit_price": str(cart_item.unit_price),
                "quantity": str(cart_item.quantity),
                "tax_percent": float(tax_percentage),
                "hs_code": getattr(cart_item.stock.product.zimra_hs_code, 'product_code', '04021099') or '04021099',
            })

        total_cost = subtotal - discount

        # Linking money portions to sale transactions and tying loose_status
        receipt_money_portions = Payment.objects.filter(payment_for="RECEIPT", created_by=request.user, loose_status=True)
        payment_methods_payload = []

        for receipt_money_portion in receipt_money_portions:
            receipt_money_portion.payment_for_id = sale_transaction.recipt_number
            receipt_money_portion.loose_status = False
            receipt_money_portion.save()

            payment_methods_payload.append({
                "moneyTypeCode": getattr(receipt_money_portion.payment_method, 'zimra_money_type_code', 0),
                "paymentAmount": float(receipt_money_portion.amount_paid),
            })

        essential.discount = 0
        essential.save()

        sale_transaction.open_state = False
        sale_transaction.save()

        # If fiscalisation is paused, skip everything below — sign nothing,
        # submit nothing, write no FiscalReceipt — and just print without
        # a QR. The sale still goes through the books.
        local_qr_string = ""
        if fiscalization_paused:
            qr_data = local_qr_string
            custome_status, message = print_receipt(sale_transaction.recipt_number, "RECEIPT", qr_data)
            print_receipt(sale_transaction.recipt_number, "(COPY)", qr_data)
            return JsonResponse({
                "custome_status": custome_status or "",
                "message": (
                    "Transaction recorded WITHOUT fiscalisation (paused). "
                    "You are responsible for issuing a compliant manual receipt."
                ),
            })

        # ---------------------------------------------------------
        # Compute Cryptographic Strings & Signatures Offline
        # ---------------------------------------------------------
        # Pre-calculate what the incremented counters should become
        next_receipt_counter = fiscal_state.receipt_counter + 1
        next_receipt_global_no = fiscal_state.receipt_global_no + 1

        # Guarantee a strictly increasing receiptDate vs the prior receipt.
        # ZIMRA's spec uses second-precision; two receipts in the same wall
        # clock second trip RCPT030 ("date earlier than previously submitted").
        receipt_dt = zimra_now()
        last_receipt = (
            FiscalReceipt.objects
            .filter(fiscal_state=fiscal_state)
            .order_by('-receipt_global_no')
            .first()
        )
        if last_receipt and last_receipt.prepared_payload:
            try:
                prior_dt = datetime.strptime(
                    last_receipt.prepared_payload['receiptDate'],
                    '%Y-%m-%dT%H:%M:%S',
                )
                # If we'd land in the same (or earlier) second, sleep just
                # long enough to roll over into the next one. Burst checkouts
                # cost at most ~1s of human-imperceptible delay.
                if receipt_dt <= prior_dt:
                    delta = (prior_dt - receipt_dt).total_seconds() + 1.0
                    time.sleep(min(delta, 2.0))
                    receipt_dt = zimra_now()
            except (KeyError, ValueError):
                pass

        mock_receipt_data = {
            "receiptType": "FISCALINVOICE",
            "receiptCurrency": "USD",
            "receiptCounter": next_receipt_counter,
            "receiptGlobalNo": next_receipt_global_no,
            "invoiceNo": str(sale_transaction.recipt_number),
            # ZIMRA expects Zimbabwe local time (CAT) regardless of host TZ.
            "receiptDate": receipt_dt,
            "receiptLines": receipt_lines_payload,
            "receiptPayments": payment_methods_payload,
        }

        # Attach buyerData only when we actually captured customer details
        if sale_transaction.buyer_name or sale_transaction.buyer_tin:
            mock_receipt_data["buyerData"] = {
                "buyerTIN": sale_transaction.buyer_tin or "",
                "buyerName": sale_transaction.buyer_name or "",
                "buyerAddress": sale_transaction.buyer_address or "",
                "buyerPhone": sale_transaction.buyer_tel or "",
                "vatNumber": sale_transaction.buyer_vat or "",
            }

        # Pre-flight validation: catch the obvious mistakes (missing tax_percent,
        # bad moneyTypeCode, payment-sum != line-sum, RCPT040 sign) BEFORE we
        # waste an ZIMRA round-trip and pollute the day with a bad receipt.
        try:
            applicable_taxes = device.applicableTaxes
        except Exception:
            applicable_taxes = {}
        validation_errors = validate_receipt_for_zimra(
            mock_receipt_data,
            applicable_taxes=applicable_taxes,
            tax_inclusive=True,
        )
        if validation_errors:
            logger.warning("Pre-flight validation failed for receipt %s: %s",
                           sale_transaction.recipt_number, validation_errors)
            return JsonResponse({
                "custome_status": "Error",
                "message": "Receipt validation failed before signing:\n- " + "\n- ".join(validation_errors),
            })

        # prepareReceipt parses your dict locally using loaded cert keys and the tracked hash chain
        prepared_receipt = device.prepareReceipt(
            mock_receipt_data,
            previousReceiptHash=fiscal_state.last_receipt_hash
        )

        local_sig_struct = prepared_receipt["receiptDeviceSignature"]
        
        # Use the same receipt_dt the signature was built around so the QR
        # url's date component matches what ZIMRA stored.
        local_qr_string = device.generate_qr_code(
            signature=local_sig_struct["signature"],
            receipt_global_no=prepared_receipt["receiptGlobalNo"],
            receipt_date=receipt_dt
        )

        # Try to submit to ZIMRA immediately. If the network is down or ZIMRA
        # is unreachable, we still keep going — the receipt is fully signed
        # and queued PENDING for the background sync worker to push later.
        # This keeps checkout latency in the happy path low while remaining
        # offline-tolerant.
        submit_response = None
        sync_status = 'PENDING'
        zimra_receipt_id = None
        try:
            submit_response = device.submitReceipt(prepared_receipt)
            sync_status = classify_submit_response(submit_response)
            if isinstance(submit_response, dict):
                zimra_receipt_id = submit_response.get('receiptID')
        except Exception as exc:
            logger.warning("ZIMRA submitReceipt failed at checkout: %s", exc)
            submit_response = {"error": str(exc)}
            sync_status = 'PENDING'

        FiscalReceipt.objects.create(
            fiscal_state=fiscal_state,
            fiscal_day_no=fiscal_state.fiscal_day_no,
            receipt_global_no=prepared_receipt["receiptGlobalNo"],
            receipt_counter=next_receipt_counter,
            receipt_type='FISCALINVOICE',
            invoice_no=str(sale_transaction.recipt_number),
            total_amount=total_cost,
            local_hash=local_sig_struct["hash"],
            local_signature=local_sig_struct["signature"],
            qr_code_string=local_qr_string,
            prepared_payload=prepared_receipt,
            sync_status=sync_status,
            zimra_receipt_id=zimra_receipt_id,
            zimra_response_log=submit_response if isinstance(submit_response, dict) else {"raw": str(submit_response)},
        )

        # Save the ongoing chain variables back to the state ledger
        fiscal_state.receipt_counter = next_receipt_counter
        fiscal_state.receipt_global_no = next_receipt_global_no
        fiscal_state.last_receipt_hash = local_sig_struct["hash"]
        fiscal_state.save()

        # ---------------------------------------------------------
        # Execute Print Out with Offline Generated QR Codes
        # ---------------------------------------------------------
        # Pass the pre-computed local_qr_string directly to your print script layers
        qr_data = local_qr_string
        custome_status, message = print_receipt(sale_transaction.recipt_number, " ", qr_data)
        print_receipt(sale_transaction.recipt_number, "(COPY)", qr_data)

        if custome_status == "":
            message = "Transaction successful"
            return JsonResponse({"custome_status": "", "message":message})
        else:
            return JsonResponse({"custome_status":custome_status, "message":message})

    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})


        
# @login_required
# @transaction.atomic 
# def check_out(request):
#     try:
#         customer_id = request.GET.get('customer_id')

#         cart_items = CartItem.objects.filter(user=request.user)
#         if cart_items:
#             pass
#         else:
#             return JsonResponse({"custome_status": "Error", "message":"You cart is empty"})
#         # creating a sale transaction
#         sale_transactions = SaleTransaction.objects.filter(created_by=request.user, open_state=True)
#         essential = ReceiptPaymentEssential.objects.filter(user=request.user)[0]
#         if sale_transactions:
#             sale_transaction = sale_transactions[0]
#             for i in sale_transactions:
#                 if i.recipt_number != sale_transaction.recipt_number:
#                     i.open_state = False
#                     i.save()
#         else:
#             new_sale_transaction = SaleTransaction()
#             new_sale_transaction.discount = essential.discount
#             new_sale_transaction.created_by = request.user

#             try:
#                 customer = CustomerAccount.objects.get(id=int(customer_id))
#                 new_sale_transaction.buyer_name = customer.company_name
#                 new_sale_transaction.buyer_tin = customer.tin_number
#                 new_sale_transaction.buyer_vat = customer.vat_number
#                 new_sale_transaction.buyer_address = customer.address
#                 new_sale_transaction.buyer_tel = customer.phone_number
#             except:
#                 pass

#             new_sale_transaction.save()

#             sale_transaction = new_sale_transaction

#         # changing cart items into sales
#         subtotal = 0
#         VAT = 0
#         total_cost = 0
#         try:
#             discount = essential.discount
#         except:
#             discount = 0


#         products_data = ""
        

#         for cart_item in cart_items:
#             new_sale = Sale()
#             new_sale.sale_transaction = sale_transaction
#             new_sale.buying_unit_price = cart_item.buying_unit_price
#             new_sale.stock = cart_item.stock
#             new_sale.selling_price = cart_item.unit_price * cart_item.quantity
#             new_sale.VAT = cart_item.VAT
#             new_sale.unit_price = cart_item.unit_price
#             new_sale.quantity = cart_item.quantity
#             new_sale.used_batches = cart_item.used_baches_data
#             new_sale.used_batch_quantities = cart_item.used_baches_quantities_data
#             new_sale.created_by = request.user

#             new_sale.save()
#             stock_quantity_notification(new_sale.stock.id)
#             cart_item.delete()

#             subtotal += cart_item.quantity * cart_item.unit_price
#             VAT += (cart_item.stock.product.vat_code.percentage/100) * (cart_item.quantity * cart_item.unit_price)


#         total_cost = (VAT + subtotal) - discount

#         # linking money portions to sale transactios and tying loose_status
#         # receipt_money_portions = ReceiptMoneyPortion.objects.filter(created_by=request.user, loose_status=True)
#         receipt_money_portions = Payment.objects.filter(payment_for="RECEIPT", created_by=request.user, loose_status=True)
#         for receipt_money_portion in receipt_money_portions:
#             receipt_money_portion.payment_for_id = sale_transaction.recipt_number


#             receipt_money_portion.loose_status = False

#             receipt_money_portion.save()

#         essential.discount = 0
#         essential.save()

#         sale_transaction.open_state = False
#         sale_transaction.save()

#         fiscalise = True
#         if fiscalise:
#             fiscalise_receipt(sale_transaction.id)

#         custome_status, message = print_receipt(sale_transaction.recipt_number, " ")
#         print_receipt(sale_transaction.recipt_number, "(COPY)")

#         if custome_status == "":
#             message = "Transaction successful"
#             return JsonResponse({"custome_status": "", "message":message})
#         else:
#             return JsonResponse({"custome_status":custome_status, "message":message})

#     except Exception as e:
#         return JsonResponse({"custome_status":"Error", "message":str(e)})



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

    total_price = subtotal + VAT
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
        qr_data = ""
        custome_status, message = print_receipt(sale_transaction.recipt_number, " ", qr_data)
        print_receipt(sale_transaction.recipt_number, " ", qr_data)
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

    total_price = subtotal + VAT


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


            # # ---------------------------------------------------
            # last_subscription = SubscriptionPayment.objects.all().order_by('created_at').last()
            # today = datetime.now()
            # if last_subscription.date_to <= today:
            #     sub = "PASS"
            #     print(sub)

            # else:
            #     sub = "FAILED"
            #     print(sub)

            #     return render(request, 'order/subscriptions/add_subscription_page.html')
            # # ---------------------------------------------------


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




