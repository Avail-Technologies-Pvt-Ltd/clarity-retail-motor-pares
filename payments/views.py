from django.shortcuts import render, redirect

from rest_framework import viewsets

from rest_framework.decorators import api_view

from rest_framework.response import Response
from rest_framework import status

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse

from reusable_functions.univesal.fiscalisation import get_fiscal_details

from pos.models import *
from enventory.models import *
from accounts.models import *
from fiscalisation.models import *
from .models import *

from datetime import datetime as datetime_
import datetime


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import locale
locale.setlocale(locale.LC_ALL, '') 

from django.db import transaction
from django.db.models import CharField, Q, F, Value as V
from django.db.models.functions import Concat, LPad, Cast

import csv

from django.views.decorators.csrf import csrf_exempt

from reusable_functions.univesal.decorators import role_validator
from reusable_functions.univesal.client_spacific_functions.client_spacific_functions import print_receipt

from django.contrib.auth.decorators import login_required

from reusable_functions.univesal.auto_billing import auto_bill

from decimal import Decimal



def configurations_error():
    return "Error: Configuration not found."

try:
    configuration = ClientSetting.objects.filter(status=True, deleted=False)[0]
    pagination_slice_leangth = configuration.pagination_slice_leangth
except:
    configurations_error()


today = str(datetime_.today().date())[:10]



# --------------------------------------------------------------------------------------------------------------



# --------------------------------------------------------------------
# HTML PAGES 
# --------------------------------------------------------------------

@login_required
def expense_types_page(request):
    return render(request, 'payments/expense_types_page.html')

@login_required
def expenses_page(request):
    auto_bill(request)
    return render(request, 'payments/expenses_page.html')

@login_required
def payment_methods_page(request):
    return render(request, 'payments/payment_methods_page.html')

@login_required
def sales_transactions_page(request):
    return render(request, 'payments/sales_transactions_page.html')

@login_required
def sales_page(request):
    return render(request, 'payments/sales_page.html')

@login_required
def VATcodes_page(request):
    return render(request, 'payments/VATcodes_page.html')
# --------------------------------------------------------------------
# //HTML PAGES
# --------------------------------------------------------------------


# --------------------------------------------------------------------
# AJAX
# --------------------------------------------------------------------


#   download


@login_required
@csrf_exempt
def download_sale_transactions_csv(request):
    date_from = ""# request.GET.get('date_from')
    date_to = ""#request.GET.get('date_to')

    sale_transactions = SaleTransaction.objects.filter(deleted=False).order_by('created_at')


    if date_from != "":
        sale_transactions = sale_transactions.filter(created_at__gte=date_from)
    if date_to != "":
        sale_transactions = sale_transactions.filter(created_at__lte=date_to)

    result = []
    for sale_transaction in sale_transactions:
        formatted_sale = {
            "Recipt Number": f"{ sale_transaction.ultimate_recipt_number }",
            "Subtotal": locale.format_string('%.2f', sale_transaction.totals['subtotal'], grouping=False),
            "VAT": locale.format_string('%.2f', sale_transaction.totals['VAT'], grouping=False),
            "Discount": locale.format_string('%.2f', sale_transaction.discount, grouping=False),
            "Total Cost": locale.format_string('%.2f', sale_transaction.totals['total_cost'], grouping=False),
            "Paid Value": locale.format_string('%.2f', sale_transaction.totals['paid_value'], grouping=False),
            "Change Left": locale.format_string('%.2f', sale_transaction.totals['change_left'], grouping=False),
            "Date": f"{ str(sale_transaction.created_at)[:10] }",
            "Buyer Name": f"{ sale_transaction.buyer_name }",
            "Buyer Tel": f"{ sale_transaction.buyer_tel }",
            "By": f"{ sale_transaction.created_by.first_name.title() } { sale_transaction.created_by.last_name.title() }"
      
        }
        result.append(formatted_sale)

    return JsonResponse({"message": "Downloaded successfully!", "sale_transactions": result})



@login_required
@csrf_exempt
def download_simple_sales_filtered_sales_csv(request):
    date_from = ""# request.GET.get('date_from')
    date_to = ""#request.GET.get('date_to')

    sales = Sale.objects.filter(deleted=False).order_by('created_at')


    if date_from != "":
        sales = sales.filter(created_at__gte=date_from)
    if date_to != "":
        sales = sales.filter(created_at__lte=date_to)

    result = []
    for sale in sales:
        formatted_sale = {
            "Product": f"{sale.stock.product.title} {sale.stock.product.details}",
            "Receipt Number": sale.sale_transaction.recipt_number,
            "Quantity": locale.format_string('%.0f', sale.quantity, grouping=False),
            "Buying Unint Price": locale.format_string('%.2f', sale.buying_unit_price, grouping=False),
            "Selling Price": locale.format_string('%.2f', sale.selling_price, grouping=False),
            "VAT": locale.format_string('%.2f', sale.VAT , grouping=False),
            "Total Price": locale.format_string('%.2f', sale.total_price, grouping=False),
            "Profit": locale.format_string('%.2f', sale.profit, grouping=False),
            "Date": str(sale.created_at)[:10]          
        }
        result.append(formatted_sale)

    return JsonResponse({"message": "Downloaded successfully!", "sales": result})




#   update
@login_required
@role_validator(['Supervisor'])
def update_expense_type(request):
    expense_type_id = request.GET.get('expense_type_id')
    title = request.GET.get('title')
    description = request.GET.get('description')
    default_price = request.GET.get('default_price')

    intervals = request.GET.get('intervals')
    reoccurring = request.GET.get('reoccurring')

    expense_type = ExpensesType.objects.get(id=int(expense_type_id))
    already_exist = ExpensesType.objects.filter(title=title, description=description)
    if already_exist.count() >1:
        return JsonResponse({"custome_status": "Error", 'message': "An expense type with the same title and description already exist!"})

    else:
        expense_type.title = title
        expense_type.description = description
        expense_type.default_price = default_price
        expense_type.reoccurring_interval = intervals
        expense_type.reoccurring = reoccurring
        expense_type.save()
        return JsonResponse({"custome_status": "", 'message': "Expense type updated successfully!"})



@login_required
@role_validator(['Supervisor'])
def update_currency(request):
    currency_id = request.GET.get('currency_id')
    rate = float(request.GET.get('rate'))
    status = request.GET.get('status')

    currency = PaymentMethod.objects.get(id=int(currency_id))
    
    currency.rate = rate
    if status == "True":
        currency.status = True
    else:
        currency.status = False
    currency.save()
    return JsonResponse({"message": "Currency updated successfully!"})


#   details

def get_expense_type_details(request):

    # try:
    expense_type_id = request.GET.get('expense_type_id')
    expense_type = ExpensesType.objects.get(id=int(expense_type_id))

    title = expense_type.title
    description = expense_type.description
    default_price = expense_type.default_price
    reoccurring = expense_type.reoccurring
    intervals = expense_type.reoccurring_interval


    details = {
        'title':title,
        'description':description,
        'default_price':default_price,
        'reoccurring': reoccurring,
        'intervals': intervals,
    }

    return JsonResponse({'details': details})
    # except Exception as e:
    #     return JsonResponse({'custome_status': "Error", 'message': f"{ e }"})


def reprint_receipt(request):
    receipt_number = request.GET.get('receipt_number')
    fiscal_details = get_fiscal_details(receipt_number)
    
    print_receipt(receipt_number, " ", fiscal_details)
    print_receipt(receipt_number, "(COPY)", fiscal_details)

    return JsonResponse({"message": "Print job successfully!"})



# @login_required
# @role_validator(['Data Analyst','Supervisor'])
# def get_expense_type_details(request):
#     expense_type_id = request.GET.get('expense_type_id')

#     expense_type = ExpensesType.objects.get(id=int(expense_type_id))

#     default_price = expense_type.default_price

#     details = {
#         'default_price': default_price
#     }
#     return JsonResponse({"details": details})



@login_required
@role_validator(['Data Analyst','Supervisor'])
def get_expense_details(request):
    expense_id = request.GET.get('expense_id')
    expense = Expense.objects.get(id=int(expense_id))

    title = expense.expense_type.title
    amount = expense.price
    date = str(expense.date)[:10]
    amount_paid = expense.amount_paid
    status = expense.status
    balance = float(amount) - float(amount_paid)
    created_by = f"{expense.created_by.first_name.title()} {expense.created_by.last_name.title()}"
    
    details = {
        "title": title,
        "amount": amount,
        "date": date,
        "amount_paid": amount_paid,
        "status": status,
        "created_by": created_by,
        "balance": balance
    }

    # expense_money_portions = ExpenseMoneyPortion.objects.filter(expense=expense)
    expense_money_portions = Payment.objects.filter(payment_for="EXPENSE", payment_for_id=int(expense.id))
    expense_money_portions_table = """
        <tr style="background: seagreen;">
            <th>Paid By</th>
            <th>Date </th>
            <th>Currency</th>
            <th style="text-align: right;">Amount Paid</th>
            <th style="text-align: right;">Rate</th>
            <th style="text-align: right;">Paid Value</th>
            <th style="text-align: right;">Manage</i></th>
        </tr>
    """
    if expense_money_portions:
        for expense_money_portion in expense_money_portions:
            expense_money_portions_table += f"""
            <tr>
                <td>{ expense_money_portion.created_by.first_name.title() } { expense_money_portion.created_by.last_name.title() }</td>
                <td>{ str(expense_money_portion.date)[:10] }</td>
                <td>{ expense_money_portion.payment_method.shortcut }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', expense_money_portion.amount_paid, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', expense_money_portion.rate, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', expense_money_portion.rated_value, grouping=True) }</td>
                <td style="text-align: right;"> <a href="" title="Delete" class="btn btn-primary" data-object-id="{ expense_money_portion.id }" type="button"  data-toggle="modal" id="delete-expense-type-modal-button"><i class="notika-icon notika-trash" onclick=(deleteExpensePaymentPortion({ expense_money_portion.id }))></a></td>
            </tr>
            """
    else:
        expense_money_portions_table = """
            <tr style="vertical-align: top; border-top: 1px solid #ccc;">
                <td style="text-align: center">No payment has been made for this expense</td>
            </tr>
        """

    return JsonResponse({"details": details, "expense_money_portions_table": expense_money_portions_table})



@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def get_currency_details(request):
    currency_id = request.GET.get('currency_id')
    currency_ = PaymentMethod.objects.get(id=int(currency_id))

    shortcut = currency_.shortcut
    currency = currency_.currency
    rate = currency_.rate
    if currency_.status == True:
        status = "True"
    else:
        status = "False"

    details = {
        "shortcut": shortcut,
        "currency": currency,
        "rate": rate,
        "status": status
    }
    return JsonResponse({"details": details})


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def get_sale_transaction_details(request):
    recipt_number = request.GET.get('recipt_number')
    sale_transaction = SaleTransaction.objects.get(recipt_number=recipt_number)

    configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]

    company_name = configuration.company_name
    address = configuration.address
    phone_number = configuration.tel
    company_registration_number = configuration.company_registration
    thank_you_message = configuration.thank_you_message
    invoice_number = sale_transaction.recipt_number
    date = str(sale_transaction.created_at)[:10]
    cashier = f"{ sale_transaction.created_by.first_name.title() } { sale_transaction.created_by.last_name.title()}"

    subtotal = sale_transaction.totals['subtotal']
    discount = sale_transaction.discount
    vat = sale_transaction.totals['VAT']
    total_cost = sale_transaction.totals['total_cost']

    change_left = sale_transaction.totals['change_left']

    dominant_payment_method_id = sale_transaction.dominant_payment_method.id
    dominant_payment_method_text = sale_transaction.dominant_payment_method.shortcut



    receipt_details = {
        "company_name": company_name,
        "address": address,
        "phone_number": phone_number,
        "company_registration_number": company_registration_number,

        "invoice_number": invoice_number,
        "date": date,
        "cashier": cashier,

        "subtotal": locale.format_string('%.2f', subtotal, grouping=True),
        "discount": locale.format_string('%.2f', discount, grouping=True),
        "vat": locale.format_string('%.2f', vat, grouping=True),
        "total_cost": locale.format_string('%.2f', total_cost, grouping=True),

        "dominant_payment_method_id": dominant_payment_method_id,
        "dominant_payment_method_text": dominant_payment_method_text,

        "thank_you_message": thank_you_message,

        "change_left": locale.format_string('%.2f', change_left, grouping=True),
    }

    products_table = f"""
        <thead>
            <tr>
                <th colspan="3">Product</th>
                <th class="number_element">Total Price</th>
                <th>Return Quantity</th>
            </tr>
        </thead>
        <tbody>
    """

    sale_transaction_products = Sale.objects.filter(sale_transaction = sale_transaction)
    for sale_transaction_product in sale_transaction_products:
        products_table += f"""
            <tr style="vertical-align: top; border-top: 1px solid #ccc;" data-id="{ sale_transaction_product.id }">
                <td>{ sale_transaction_product.quantity }</td>
                <td> x &nbsp &nbsp</td>
                <td style="width: 70%">  { sale_transaction_product.stock.product.title } { sale_transaction_product.stock.product.details }</td>
                <td class="number_element">{ locale.format_string('%.2f', sale_transaction_product.selling_price, grouping=True) }&nbsp &nbsp</td>
                <td>
                    <input class="item-input recept-item" 
                           type="number" 
                           min="0" 
                           max="{ sale_transaction_product.actual_sales }" 
                           value="0" 
                           style="width: 50px">
                    <input type="hidden" class="unit-price" value="{ sale_transaction_product.unit_price }">
                </td>
            </tr>
        """
    products_table += f"</tbody>"


    receipt_money_portions_table = f"""
        <tr>
            <th>CURRENCY </th>
            <th style='text-align: right' class=""> AMOUNT </th>
            <th style='text-align: right' class=""> RATE </th>
            <th style='text-align: right' class=""> VALUE</th>
        </tr>
    """

    # receipt_money_portions = ReceiptMoneyPortion.objects.filter(sale_transaction=sale_transaction)
    receipt_money_portions = Payment.objects.filter(payment_for="RECEIPT", payment_for_id=sale_transaction.recipt_number)
    for receipt_money_portion in receipt_money_portions:
        receipt_money_portions_table += f"""
        <tr style="vertical-align: top; border-top: 1px solid #ccc;">
            <td>{ receipt_money_portion.payment_method.shortcut }</td>
            <td style='text-align: right; '>{ locale.format_string('%.2f', receipt_money_portion.amount_paid, grouping=True) }</td>
            <td style='text-align: right; '>{ locale.format_string('%.2f', receipt_money_portion.rate, grouping=True) }</td>
            <td style='text-align: right; '>{ locale.format_string('%.2f', receipt_money_portion.rated_value, grouping=True) }</td>
        </tr>
        """
    return JsonResponse({"receipt_details":receipt_details, "receipt_money_portions_table": receipt_money_portions_table, "products_table": products_table})


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def get_sale_details(request):
    sale_id = request.GET.get('sale_id')
    sale = Sale.objects.get(id=sale_id)

    product_title = sale.stock.product.title
    product_details = sale.stock.product.details
    profit = sale.profit
    selling_price = sale.selling_price
    vat = sale.VAT
    average_unit_cost = sale.buying_unit_price
    unit_price = sale.unit_price
    quantity = sale.quantity
    receipt = (sale.sale_transaction.ultimate_recipt_number)
    cashier = f"{ sale.created_by.first_name.title() } { sale.created_by.first_name.title() }"
    date = str(sale.created_at)[:10]

    # total_units = sale.total_units

    details = {
        "product_title": product_title,
        "product_details": product_details,
        "profit": locale.format_string('%.2f', profit, grouping=True),
        "selling_price": locale.format_string('%.2f', selling_price, grouping=True),
        "vat": locale.format_string('%.2f', vat, grouping=True),
        "average_unit_cost": locale.format_string('%.2f', average_unit_cost, grouping=True),
        "quantity": locale.format_string('%.0f', quantity, grouping=True),
        "receipt": receipt,
        "cashier": cashier,
        "date": date,
        "unit_price":unit_price,
    }

    return JsonResponse({"details":details})



#   add
@login_required
@role_validator(['Supervisor'])
def add_credit_note_refund_money_portion(request):
    try:
        payment_method = request.GET.get('payment_method')
        amount = request.GET.get('amount')
        credit_note_id = request.GET.get('credit_note_id')
        date_paid = request.GET.get('date_paid')


        if float(amount) == 0:
            return JsonResponse({"custome_status":"Error", "message":"Amount can not be 0"})


        # new_credit_note_refund_money_portion = RefundReturnInnMoneyPortion()
        new_credit_note_refund_money_portion = Payment()
        new_credit_note_refund_money_portion.payment_for = "CREDIT_NOTE"
        new_credit_note_refund_money_portion.payment_for_id = int(credit_note_id)
        new_credit_note_refund_money_portion.payment_method = PaymentMethod.objects.get(id=int(payment_method))
        new_credit_note_refund_money_portion.rate = PaymentMethod.objects.get(id=int(payment_method)).rate
        new_credit_note_refund_money_portion.amount_paid = amount
        new_credit_note_refund_money_portion.date = date_paid
        new_credit_note_refund_money_portion.created_by = request.user
        new_credit_note_refund_money_portion.save()
        return JsonResponse({"message":"Payment recorded successfully!"})
    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":f'{e}'})



@login_required
@role_validator(['Supervisor'])
def add_return_out_refund_money_portion(request):
    try:
        payment_method = request.GET.get('payment_method')
        amount = request.GET.get('amount')
        date_paid = request.GET.get('date_paid')
        return_out_id = request.GET.get('return_out_id')

        if float(amount) == 0:
            return JsonResponse({"custome_status":"Error", "message":"Amount can not be 0"})



        # new_return_out_refund_money_portion = RefundReturnOutMoneyPortion()
        new_return_out_refund_money_portion = Payment()
        new_return_out_refund_money_portion.payment_for = "RETURN_OUT_REFUND"
        new_return_out_refund_money_portion.payment_for_id = int(return_out_id)
        new_return_out_refund_money_portion.payment_method = PaymentMethod.objects.get(id=int(payment_method))
        new_return_out_refund_money_portion.rate = PaymentMethod.objects.get(id=int(payment_method)).rate
        new_return_out_refund_money_portion.amount_paid = amount
        new_return_out_refund_money_portion.date = date_paid
        new_return_out_refund_money_portion.created_by = request.user
        new_return_out_refund_money_portion.save()
        return JsonResponse({"message":"Payment recorded successfully!"})
    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":f"{e}"})





@login_required
@role_validator(['Supervisor'])
def add_expense_money_portion(request):
    try:
        expense_id = request.GET.get('expense_id')
        expense = Expense.objects.get(id=int(expense_id))

        payment_method = request.GET.get('payment_method')
        payment_method = PaymentMethod.objects.get(id=payment_method)
        amount = request.GET.get('amount')
        date_paid = request.GET.get('date_paid')

        new_expense_money_portion = Payment()
        new_expense_money_portion.payment_for = "EXPENSE"
        new_expense_money_portion.payment_for_id = expense.id
        new_expense_money_portion.payment_method = payment_method
        new_expense_money_portion.rate = payment_method.rate
        new_expense_money_portion.amount_paid = amount
        new_expense_money_portion.date = date_paid
        new_expense_money_portion.created_by = request.user
        new_expense_money_portion.loose_status = False

        new_expense_money_portion.save()

        return JsonResponse({'custom_status': "", 'message': "Payment recorded successfully!"})
    
    except (Expense.DoesNotExist, PaymentMethod.DoesNotExist) as e:
        return JsonResponse({'custom_status': "error", 'message': f'Record not found: {str(e)}'}, status=404)
    
    except Exception as e:
        return JsonResponse({'custom_status': "error", 'message': f'Error: {str(e)}'}, status=500)


@login_required
@role_validator(['Supervisor'])
def add_invoice_money_portion_for_existing_invoice(request):
    try:
        payment_method = request.GET.get('payment_method')
        amount = request.GET.get('amount')
        invoice_id = request.GET.get('invoice_id')
        date_paid = request.GET.get('date_paid')

        payment_method = PaymentMethod.objects.get(id=int(payment_method))
        invoice = Invoice.objects.get(id=int(invoice_id))

        # new_invoice_money_portion = InvoiceMoneyPortion()
        new_invoice_money_portion = Payment()
        new_invoice_money_portion.invoice = invoice
        new_invoice_money_portion.payment_method = payment_method
        new_invoice_money_portion.rate = payment_method.rate
        new_invoice_money_portion.amount_paid = amount
        new_invoice_money_portion.payment_for = "INVOICE"
        new_invoice_money_portion.payment_for_id = invoice_id
        new_invoice_money_portion.date = date_paid
        new_invoice_money_portion.created_by = request.user
        new_invoice_money_portion.loose_status = False
        new_invoice_money_portion.save()
    except Exception as e:
        return JsonResponse({'custome_status':"Error", 'message':str(e)})

    return JsonResponse({'custome_status':"", 'message':"Payment recorded successfully!"})


@login_required
@role_validator(['Supervisor'])
def add_invoice_payment_portion(request):
    payment_method_id = request.GET.get('payment_method_id')
    payment_method = PaymentMethod.objects.get(id=payment_method_id)
    paid = request.GET.get('paid')

    try:
        existing_invoice_money_portion = Payment.objects.filter(payment_for="INVOICE", loose_status=True, created_by=request.user, payment_method=payment_method)
        if existing_invoice_money_portion:
            invoice_money_portion = existing_invoice_money_portion.first()
            invoice_money_portion.amount_paid += Decimal(paid)
            invoice_money_portion.save()

        else:
            # new_invoice_money_portion = InvoiceMoneyPortion()
            new_invoice_money_portion = Payment()
            new_invoice_money_portion.payment_method = payment_method
            new_invoice_money_portion.rate = payment_method.rate
            new_invoice_money_portion.payment_for = "INVOICE"
            new_invoice_money_portion.payment_for_id = 0
            new_invoice_money_portion.loose_status = True
            new_invoice_money_portion.date = today
            new_invoice_money_portion.amount_paid = paid
            new_invoice_money_portion.created_by = request.user
            new_invoice_money_portion.save()

    except Exception as e:
        return JsonResponse({'custome_status':"Error", 'message':str(e)})

    return JsonResponse({'custome_status':"", 'message':"Expense recorded successfully!"})


@login_required
@role_validator(['Supervisor'])
def add_expense(request):
    expense_type = request.GET.get('expense_type')
    description = request.GET.get('description')
    date = request.GET.get('date')
    price = request.GET.get('price')

    # try:
    new_expense = Expense()

    new_expense.expense_type = ExpensesType.objects.get(id=int(expense_type))
    new_expense.description = description
    new_expense.date = date
    new_expense.price = price
    new_expense.created_by = request.user

    new_expense.save()
    # except Exception as e:
    #     return JsonResponse({'custome_status':"Error", 'message':e})    

    return JsonResponse({'custome_status':"", 'message':"Expense recorded successfully!"})


@login_required
@role_validator(['Supervisor'])
def add_expense_type(request):
    title = request.GET.get('title')
    description = request.GET.get('description')
    default_price = request.GET.get('default_price')
    reoccurring = request.GET.get('reoccurring')
    intervals = request.GET.get('intervals')

    already_exist = ExpensesType.objects.filter(title=title)
    if already_exist:
        return JsonResponse({'custome_status':"Error", 'message':"Error! An expense with the same title already exist in your system"})
    else:
        new_expense_type = ExpensesType()

        new_expense_type.title = title
        new_expense_type.description = description
        new_expense_type.default_price = default_price
        new_expense_type.reoccurring = reoccurring
        new_expense_type.reoccurring_interval = intervals
        new_expense_type.created_by = request.user

        new_expense_type.save()

    return JsonResponse({'custome_status':"", 'message':"Expense type created successfully!"})



@login_required
@role_validator(['Supervisor'])
def add_currency(request):
    currency = request.GET.get('currency')
    shortcut = request.GET.get('shortcut')
    rate = request.GET.get('rate')

    already_exist = PaymentMethod.objects.filter(currency=currency)
    if already_exist:
        return JsonResponse({'custome_status':"Error", 'message':"Error! A currency with the same title already exist in your system"})

    already_exist = PaymentMethod.objects.filter(shortcut=shortcut)
    if already_exist:
        return JsonResponse({'custome_status':"Error", 'message':"Error! A currency with the same shortcut already exist in your system"})

    else:
        new_payment_method = PaymentMethod()

        new_payment_method.currency = currency
        new_payment_method.shortcut = shortcut
        new_payment_method.rate = rate
        new_payment_method.created_by = request.user

        new_payment_method.save()

    return JsonResponse({'custome_status':"", 'message':"Currency created successfully!"})


@login_required
@role_validator(['Supervisor'])
def add_vat_code(request):
    title = request.GET.get('title')
    percentage = request.GET.get('percentage')
    status = request.GET.get('status')

    already_exist = VATCode.objects.filter(title=title)
    if already_exist:
        return JsonResponse({'custome_status':"Error", 'message':"Error! A VAT Code with the same title already exist in your system"})

    else:
        new_vat_code = VATCode()
        new_vat_code.title = title
        new_vat_code.percentage = percentage
        new_vat_code.created_by = request.user
        if status == "False":
            new_vat_code.status = False

        new_vat_code.save()

    return JsonResponse({'custome_status':"", 'message':"VAT Code created successfully!"})




#   delete
@login_required
@role_validator(['Supervisor'])
def delete_expense_type(request):
    try:
        expense_type_id = request.GET.get('expense_type_id')
        expense_type = ExpensesType.objects.get(id=int(expense_type_id))
        is_being_used = Expense.objects.filter(expense_type=expense_type)
        if is_being_used:
            return JsonResponse({'custome_status':"Error", 'message':"Sorry, this expense type is already being used. Some expenses depends on it, there for can not be deleted."})
        else:
            expense_type.delete()
            return JsonResponse({'custome_status':"", 'message':"Expense type deleted successfully!"})

    except Exception as e:
        return JsonResponse({'custome_status':"Error", 'message':f"{ e }"})


@login_required
@role_validator(['Supervisor'])
def delete_expense(request):
    try:
        expense_id = request.GET.get('expense_id')
        expense = Expense.objects.get(id=int(expense_id))
        # is_being_used = ExpenseMoneyPortion.objects.filter(expense=expense_id)
        is_being_used = Payment.objects.filter(payment_for="EXPENSE", payment_for_id=int(expense_id))
        if is_being_used:
            return JsonResponse({'type':"error",'title':"Error", 'message':"For security reasons, you have to delete all payments for this bill first"})
        else:
            expense.delete()
            return JsonResponse({'type':"success",'title':"Deleted", 'message':"Expense deleted successfully!"})

    except Exception as e:
        return JsonResponse({'type':"error",'title':"Error", 'message':f"{ e }"})



@login_required
@role_validator(['Supervisor'])
def delete_invoice_money_portion(request):
    try:
        invoice_money_portion_id = request.GET.get('invoice_money_portion_id')
        # invoice_money_portion = InvoiceMoneyPortion.objects.get(id=invoice_money_portion_id)
        invoice_money_portion = Payment.objects.get(id=int(invoice_money_portion_id))
        invoice_money_portion.delete()
    except Exception as e:
        return JsonResponse({'title':"Error", 'message':str(e), 'type': "error"})
    return JsonResponse({'title':"Deleted", 'message':"Payment deleted successfully!", 'type': "success"})


@login_required
@role_validator(['Supervisor'])
def delete_expense_money_portion(request):
    try:
        expense_money_portion_id = request.GET.get('payment_portion_id')
        # expense_money_portion = ExpenseMoneyPortion.objects.get(id=expense_money_portion_id)
        expense_money_portion = Payment.objects.get(payment_for="EXPENSE", payment_for_id=int(expense_money_portion_id))
        expense_money_portion.delete()
    except Exception as e:
        return JsonResponse({'title':"Failed To Delete", 'message':e, 'type':"error"})
    return JsonResponse({'title':"Deleted", 'type':"success",'message':"Payment deleted successfully!"})



#   listing
@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_transactions_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        transactions = SaleTransaction.objects.filter(deleted=False).order_by('created_at').reverse()


    if request_type == "FORM-FILTER":
        # form filterr here
        transactions = SaleTransaction.objects.filter(deleted=False)

        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        receipt_number = request.GET.get('receipt_number')

        if date_from != "":
            transactions = transactions.filter(created_at__date__gte=date_from)
        if date_to != "":
            transactions = transactions.filter(created_at__date__lte=date_to)
        if receipt_number != "":
            # Fetch all matching transactions first
            transactions_list = list(transactions)
            
            # Filter in Python using your property
            filtered_transactions = []
            for transaction in transactions_list:
                if receipt_number.lower() in transaction.ultimate_recipt_number.lower():
                    filtered_transactions.append(transaction)
            
            # Get IDs and filter the original queryset
            transaction_ids = [t.recipt_number for t in filtered_transactions]
            transactions = transactions.filter(recipt_number__in=transaction_ids)
    
    #------------------------------------------------------------------------------ 
    data_queryset = transactions
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
                <th>Recipt Number</th>
                <th style="text-align: right;">Subtotal</th>
                <th style="text-align: right;">Discount</th>
                <th style="text-align: right;">VAT</th>
                <th style="text-align: right;">Total Cost</th>
                <th style="text-align: right;">Paid Value</th>
                <th style="text-align: right;">Change Left</th>
                <th style="text-align: right;">Profit</th>
                <th>Sales Rep</th>
                <th>Date</th>
                <th colspan="2">Action</th>
            </tr>
        </thead>
    """
    rows = ""
    for transaction in data_page:
        row = f"""
            <tr>
                <td title="View Details">{ transaction.ultimate_recipt_number } </td>
                <td style="text-align: right;">{ locale.format_string('%.2f', transaction.totals['subtotal'], grouping=True) } </td>
                <td style="text-align: right;">{ locale.format_string('%.2f', transaction.discount, grouping=True) } </td>
                <td style="text-align: right;">{ locale.format_string('%.2f', transaction.totals['VAT'], grouping=True) } </td>
                
                <td style="text-align: right;">{ locale.format_string('%.2f', transaction.totals['total_cost'], grouping=True) } </td>
                <td style="text-align: right;">{ locale.format_string('%.2f', transaction.totals['paid_value'], grouping=True) } </td>
                <td style="text-align: right;">{ locale.format_string('%.2f', transaction.totals['change_left'], grouping=True) } </td>
                <td style="text-align: right;">{ locale.format_string('%.2f', transaction.totals['profit'], grouping=True) } </td>

                <td>{ transaction.created_by.username.title() }</td>
                <td>{ str(transaction.created_at)[:10] }</td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ transaction.recipt_number }" type="button"  data-toggle="modal" data-target="#saleTransactionDetailsModal" id="sale-transaction-details-modal-button"><i class="notika-icon notika-menus"></a></td>
                <td><a href="" title="Return Inn" class="btn btn-primary" data-object-id="{ transaction.recipt_number }" type="button"  data-toggle="modal" data-target="#returnSaleTransactionItemsModal" id="sale-transaction-details-modal-button"><i class="notika-icon notika-next"></a></td>
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
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer



    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'data':data_page})



def load_invoice_payment_portions_data(request):
    # invoice_money_portions = InvoiceMoneyPortion.objects.filter(assigned=False, created_by=request.user)
    invoice_money_portions = Payment.objects.filter(payment_for="INVOICE", loose_status=True, created_by=request.user)
    #  getting the required amounts  ==============================================================================================
    try:
        discount = ReceiptPaymentEssential.objects.filter(user=request.user)[0].discount
    except:
        discount = 0

    total_cost = 0
    required_amount = 0
    subtotal = 0
    VAT = 0
    paid_value = 0
    
    temporary_invoices = TemporaryInvoice.objects.filter(created_by=request.user)
    if temporary_invoices:
        temporary_invoice = temporary_invoices[0]
            
        for i in temporary_invoices:
            if temporary_invoice != i:
                i.delete()

        temporary_invoice_items = TemporaryInvoiceItem.objects.filter(invoice=temporary_invoice)
        if temporary_invoice_items:
            for temporary_invoice_item in temporary_invoice_items:
                new_line_discount = float(temporary_invoice_item.discount_price)
                new_line_subtotal = float(temporary_invoice_item.buying_pack_price * temporary_invoice_item.total_packs)
                new_line_VAT = float((float(temporary_invoice_item.stock.product.vat_code.percentage)/100)*(new_line_subtotal))
                new_line_total_cost = new_line_subtotal + new_line_VAT

                subtotal = float(subtotal) + new_line_subtotal
                VAT = float(VAT) + new_line_VAT
                total_cost = float(total_cost) + new_line_VAT + new_line_subtotal
                discount = float(discount) + float(new_line_discount)

    
    invoice_total_cost = subtotal - discount + VAT


    # ==========================================================================================================================
    invoice_money_portions_table_rows = []
    for invoice_money_portion in invoice_money_portions:
        rated_amount = float(invoice_money_portion.amount_paid) / float(invoice_money_portion.rate)
        row = [
            f"{ invoice_money_portion.id }",
            f"{ invoice_money_portion.payment_method.shortcut }",
            f"{ locale.format_string('%.2f', invoice_money_portion.amount_paid, grouping=True)}",
            f"{ locale.format_string('%.2f', invoice_money_portion.rate, grouping=True)}",
            f"{ locale.format_string('%.2f', rated_amount, grouping=True)}"
        ]

        invoice_money_portions_table_rows.append(row)
        paid_value += rated_amount

    required_amount = float(invoice_total_cost) - float(paid_value)
    

    totals = {
        "total_invoice_cost": locale.format_string('%.2f', float(total_cost), grouping=True),
        "total_invoice_paid_value": locale.format_string('%.2f', float(paid_value), grouping=True),
        "required_amount": locale.format_string('%.2f', float(required_amount), grouping=True),
    }

    return JsonResponse({"invoice_money_portions_table_rows": invoice_money_portions_table_rows, "totals":totals})




@login_required
@role_validator(['Data Analyst','Supervisor'])
def ajax_expenses_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        expenses = Expense.objects.filter(deleted=False).order_by('-date')


    if request_type == "FORM-FILTER":
        # form filterr here
        expenses = Expense.objects.filter(deleted=False).order_by('-date')

        date_from = request.GET.get('from')
        date_to = request.GET.get('to')
        reoccurring = request.GET.get('reoccurring')
        reoccurring_interval = request.GET.get('reoccurring_interval')
        category_id = request.GET.get('category_id')


        if date_from != "":
            expenses = expenses.filter(date__date__gte=date_from)
        if date_to != "":
            expenses = expenses.filter(date__date__lte=date_to)
        if reoccurring != "All":
            expenses = expenses.filter(expense_type__reoccurring=reoccurring)
        if reoccurring_interval != "All":
            expenses = expenses.filter(expense_type__reoccurring_interval=reoccurring_interval)
        if category_id != "" and category_id != "0" and category_id != "All":
            expenses = expenses.filter(expense_type__id=int(category_id))


    #------------------------------------------------------------------------------ 
    data_queryset = expenses
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
                <th>Date</th>
                <th>Expense</th>
                <th style="text-align: right;">Amount</th>
                <th style="text-align: right;">Paid</th>
                <th style="text-align: right;">Balance</th>
                <th>Status</th>
                <th colspan="3">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for expense in data_page:
        if expense.status == "CHANGE":
            status = f""" <td> <span style="background: blue; padding: 5px; color: white; border-radius: 15px;">{ expense.status }</span> </td> """
        elif expense.status == "CLEARED":
            status = f""" <td> <span style="background: green; padding: 5px; color: white; border-radius: 15px;">{ expense.status }</span> </td> """
        elif expense.status == "BALANCE":
            status = f""" <td> <span style="background: red; padding: 5px; color: white; border-radius: 15px;">{ expense.status }</span> </td> """
        else:
            status = f""" <td>{ expense.status }</td> """

        row = f"""
            <tr id="expense-row-{ expense.id }">
                <td>{ str(expense.date)[:10] }</td>                
                <td>
                    { expense.expense_type }<br>
                    <small>{ expense.description }</small>
                </td>
                <td style="text-align: right;">{ locale.format_string('%.2f', expense.price, grouping=True) } </td>
                <td style="text-align: right;">{ locale.format_string('%.2f', expense.amount_paid, grouping=True) } </td>
                <td style="text-align: right;">{ locale.format_string('%.2f', expense.balance, grouping=True) } </td>
                { status }
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ expense.id }" type="button"  data-toggle="modal" data-target="#expenseDetailsModal" id="expense-details-modal-button-{ expense.id }"><i class="notika-icon notika-menus"></i></a></td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ expense.id }" type="button"  data-toggle="modal" data-target="#updateExpenseModal" id="update-expense-modal-button-{ expense.id }"><i class="notika-icon notika-edit"></i></a></td>
                <td style="text-align: right;"><button onclick="deleteExpense({ expense.id })">🗑️</button></td>                
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
                <td></td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer


    table_summery = f" {expenses.count()} out of {Expense.objects.all().count()} expenses."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})




@login_required
@role_validator(['Data Analyst','Supervisor'])
def ajax_expense_types_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        expense_types = ExpensesType.objects.filter(deleted=False).order_by("title")


    if request_type == "FORM-FILTER":
        # form filterr here
        expense_types = ExpensesType.objects.filter(deleted=False).order_by("title")
        
        title = request.GET.get('title') 
        method = request.GET.get('method') 
        interval = request.GET.get('interval')


        if title != "":
            expense_types = expense_types.filter(title__icontains=title)
        if method != "All":
            expense_types = expense_types.filter(reoccurring=method)
        if interval != "All":
            expense_types = expense_types.filter(reoccurring_interval=interval)



    
    #------------------------------------------------------------------------------ 
    data_queryset = expense_types
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
                <th>Expense Type</th>
                <th style="text-align: left">Billing Method</th>
                <th style="text-align: right">Defalt Price</th>
                <th style="width:10%" colspan="2">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for expense_type in data_page:
        row = f"""
            <tr>
                <td>
                    { expense_type.title }<br>
                    <small style="text-align: left">{ expense_type.description }</small>
                </td>
                <td>
                    { expense_type.billing_method_d }
                    <div class="badge">{ expense_type.reoccurring_interval_d }</div>
                </td>
                
                <td style="text-align: right">{ locale.format_string('%.2f', expense_type.default_price, grouping=True) } </td>
                <td> <a href="" title="Update" class="btn btn-primary" data-object-id="{ expense_type.id }" type="button"  data-toggle="modal" data-target="#updateExpenseTypeModal" id="update-expense-type-modal-button"><i class="notika-icon notika-edit"></a></td>
                <td> <a href="" title="Delete" class="btn btn-primary" data-object-id="{ expense_type.id }" type="button"  data-toggle="modal" data-target="#deleteExpenseTypeModal" id="delete-expense-type-modal-button"><i class="notika-icon notika-trash" onclick=(deleteExpenseType({ expense_type.id }))></a></td>

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


    table_summery = f" {expense_types.count()} out of {ExpensesType.objects.filter(deleted=False).count()} expense types."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})



@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_sales_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # on initial load the returned sales are not displayed, but in form filter they are displayed
        if search_field == "all":
            sales = Sale.objects.annotate(
                full_text = Concat(
                    'sale_transaction', V(' '),'stock__product__title', V(' '), 'stock__product__details', output_field=CharField()
                    )
                ).filter(deleted=False, full_text__icontains=search_key).exclude(quantity__lte=F('total_returned')).order_by('created_at').reverse()

        elif search_field == "Stock":
            sales = Sale.objects.filter(stock__product__title__icontains=search_key).order_by('created_at').reverse()

        else:
            pass

    configuration = ClientSetting.objects.filter(deleted=False, status=True).first()
    prefix = configuration.invoice_number_prefix if configuration else ''

    if request_type == "FORM-FILTER":
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        receipt_number = request.GET.get('receipt_number')
        product_code = request.GET.get('product_code').upper()
        
        sales = Sale.objects.filter(deleted=False).order_by('created_at').reverse()
        if receipt_number != "":
            sales = sales.annotate(
                full_receipt_number=Concat(
                    V(prefix),
                    LPad(
                        Cast(F('sale_transaction__recipt_number'), output_field=CharField()),
                        6,
                        V('0')
                    ),
                    output_field=CharField()
                )
            ).filter(full_receipt_number__icontains=receipt_number)
        if date_from != "":
            sales = sales.filter(created_at__date__gte=date_from)
        if date_to != "":
            sales = sales.filter(created_at__date__lte=date_to)
        if product_code != "":
            sales = sales.filter(stock__product__product_code=product_code)
        

    
    #------------------------------------------------------------------------------ 
    data_queryset = sales
    paginator = Paginator(data_queryset, pagination_slice_leangth)
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
                <th>Receipt</th>
                <th>Product</th>
                <th style="text-align: right;">Quantity</th>
                <th style="text-align: right;">Returned</th>
                <th style="text-align: right;">S Unit Price</th>
                <th style="text-align: right;">Total Price</th>
                <th style="text-align: right;">Profit</th>
                <th>Date</th>
                <th colspan="1">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for sale in data_page:
        # <td>{ locale.format_string('%.0f', sale.total_repeats, grouping=True) }</td>
        row = f"""
            <tr>
                <th>{ sale.sale_transaction.ultimate_recipt_number } </th>
                <th>({ sale.stock.product.product_code.upper() }) <small>{ sale.stock.product.details.capitalize() }</small></th>
                <td style="text-align: right;">{ locale.format_string('%.0f', sale.quantity, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.0f', sale.total_returned, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', sale.unit_price, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', sale.total_price, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', sale.profit, grouping=True) }</td>
                <td>{ str(sale.created_at)[:10] }</td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ sale.id }" type="button"  data-toggle="modal" data-target="#saleDetailsModal" id="sale-details-modal-button"><i class="notika-icon notika-menus"></a></td>
                

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
                <td></td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer


    table_summery = f" {sales.count()} out of {Sale.objects.all().count()} sales."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})




@login_required
def ajax_currencies_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        currencies = PaymentMethod.objects.filter(deleted=False).order_by("shortcut")


    if request_type == "FORM-FILTER":
        # form filterr here
        currencies = PaymentMethod.objects.filter(deleted=False).order_by("shortcut")

    
    #------------------------------------------------------------------------------ 
    data_queryset = currencies
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
                <th>Symbol</th>
                <th style="text-align:right;">RATE (USD:1)</th>
                <th>Currency</th>
                <th>Last Update</th>
                <th>Updated by</th>
                <th>Active</th>
                <th>Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for currency in data_page:
        row = f"""
            <tr>
                <th>{ currency.shortcut }</th>
                <th style="text-align:right;">{ locale.format_string('%.2f', currency.rate, grouping=True) }</th>
                <td>{ currency.currency } </td>
                <td>{ str(currency.updated_at)[:10] }</td>
                <td>{ currency.created_by.first_name.title() } { currency.created_by.first_name.title() }</td>
                <td><a href="enable_disable_currency/{ currency.id }">{ currency.status }</a></td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ currency.id }" type="button"  data-toggle="modal" data-target="#updateCurrencyModal" id="update-currency-modal-button"><i class="notika-icon notika-edit"></a></td>
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
                <td></td>
                <td></td>
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer


    table_summery = f" {currencies.count()} out of {PaymentMethod.objects.all().count()} currencies."
    print(f"DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD: {str(data_page)}")
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})





@login_required
def ajax_vat_codes_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        vat_codes = VATCode.objects.filter(deleted=False)


    if request_type == "FORM-FILTER":
        # form filterr here
        vat_codes = VATCode.objects.filter(deleted=False)

    
    #------------------------------------------------------------------------------ 
    data_queryset = vat_codes
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
                <th>Title</th>
                <th>Percentage</th>
                <th>Created by</th>
                <th>Date</th>
            </tr>
        </thead>
    """
    rows = ""
    for vat_code in data_page:
        row = f"""
            <tr>
                <td>{ vat_code.title }</a></td>
                <td>{ vat_code.percentage } </td>
                <td>{ vat_code.created_by.first_name.title() } </td>
                <td>{ str(vat_code.created_at)[:10] }</td>
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
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer


    table_summery = f" {vat_codes.count()} out of {VATCode.objects.all().count()} vat_codes."
    print(f"DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD: {str(data_page)}")
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})





# 
@login_required
@role_validator(['Sales Rep'])
@transaction.atomic
def add_reciept_payment_portion(request):
    paying_currency_id = request.GET.get('paying_currency_id')
    currency = PaymentMethod.objects.get(id=int(paying_currency_id))
    discount = float(request.GET.get('discount'))
    paid = float(request.GET.get('paid'))
    change = float(request.GET.get('change'))
    change_given = float(request.GET.get('change_given'))

    rated_discount = float(discount)/float(currency.rate)



    # handling essentials
    essentials = ReceiptPaymentEssential.objects.filter(user=request.user)
    if essentials:
        essential = essentials[0]
        for i in essentials:
            if i.id != essential.id:
                i.delete()
    else:
        essential = ReceiptPaymentEssential()
        essential.discount = 0
        essential.user = request.user

        essential.save()

    # altering essintial acodingly
    essential.discount = rated_discount + float(essential.discount)
    essential.save()

    # creating money portion
    #   check if currence alredy exixt
    # money_portions = ReceiptMoneyPortion.objects.filter(created_by=request.user, loose_status=True)
    money_portions = Payment.objects.filter(payment_for="RECEIPT", created_by=request.user, loose_status=True)
    existing_currency_portions = money_portions.filter(payment_method=currency)
    if existing_currency_portions:
        existing_currency_portion = existing_currency_portions[0]
        existing_currency_portion.amount_paid = float(existing_currency_portion.amount_paid) + float(paid)

        existing_currency_portion.save()

    else:
        # the portion is of a new currency in the portions list, therefor create new portion
        # new_receipt_money_portion = ReceiptMoneyPortion()
        new_receipt_money_portion = Payment()
        new_receipt_money_portion.loose_status = True
        new_receipt_money_portion.payment_method = currency
        new_receipt_money_portion.rate = currency.rate
        new_receipt_money_portion.payment_for = "RECEIPT"
        new_receipt_money_portion.payment_for_id = 0
        new_receipt_money_portion.amount_paid = float(paid)
        new_receipt_money_portion.date = today
        new_receipt_money_portion.change = float(change)
        new_receipt_money_portion.change_given = float(change_given)
        new_receipt_money_portion.created_by = request.user

        new_receipt_money_portion.save()


    return JsonResponse({"custome_status":"", "message":"Money Portion added successfully"})




@login_required
def get_paying_currency_details(request):
    paying_currency_id = request.GET.get('paying_currency_id')

    paying_currency = PaymentMethod.objects.get(id=int(paying_currency_id))
    paying_currency = {
        "id": paying_currency.id,
        "currency": paying_currency.currency,
        "shortcut": paying_currency.shortcut,
        "rate": paying_currency.rate
    }
    
    return JsonResponse({"paying_currency": paying_currency})


#   options

@login_required
def load_live_expense_type_options(request):
    search_query = request.GET.get('search_query')

    expense_types_ = ExpensesType.objects.filter(deleted=False, title__icontains=search_query)[:50]
    expense_types = [
        f"<option value='{ expense_type.id }'> { expense_type.title } </option>" for expense_type in expense_types_
    ]

    title_option = [
        f"<option value='0'>Select Expense Type</option>"
    ]

    expense_types = title_option + expense_types

    return JsonResponse({'options':expense_types})


@login_required
def load_live_vat_code_options(request):
    search_query = request.GET.get('search_query')

    vat_codes_ = VATCode.objects.filter(deleted=False, title__icontains=search_query)[:50]
    vat_codes = [
        f"<option value='{ vat_code.id }'> { vat_code.title } ({ vat_code.percentage }%) </option>" for vat_code in vat_codes_
    ]


    return JsonResponse({'options':vat_codes})




@login_required
def load_payment_method_options(request):
    try:
        search_query = request.GET.get('search_query')
        payment_methods_ = PaymentMethod.objects.annotate(
            full_text = Concat(
                'currency', V(' '), 'shortcut', output_field=CharField()
                )
            ).filter(deleted=False, status=True, full_text__icontains=search_query)[:50]
            
    except:
        payment_methods_ = PaymentMethod.objects.filter(deleted=False, status=True)[:50]
        
    payment_methods = [
        f"<option value='{ payment_method.id }'> { payment_method.shortcut } { payment_method.rate } </option>" for payment_method in payment_methods_
    ]

    #recent_payment_method
    recent_payment_method = []
    try:
        recent_payment_method = MoneyPortion.objects.filter(towards__created_by=request.user).exclude(payment_method=None).last().payment_method
        recent_payment_method = [
        f"<option selected  value='{ recent_payment_method.id }'>  { recent_payment_method.shortcut } [{ recent_payment_method.rate }]</option>"
        ]
    except:
        recent_payment_method = []



    title_option = [
        f"<option value='0'>Select Payment Method</option>"
    ]
    

    payment_methods = title_option + payment_methods
    if len(recent_payment_method) != 0:
        payment_methods = recent_payment_method + payment_methods

    return JsonResponse({'options':payment_methods})

# --------------------------------------------------------------------
# //AJAX
# --------------------------------------------------------------------

