from django.shortcuts import render, redirect

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse

from .forms import AddUserForm, UpdateUserForm
from .models import User, Supplier, Manufacturer, ClientSetting
from enventory.models import *
from payments.models import *

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, logout 
from django.contrib.auth import login as built_inn_login_function

from django.contrib import messages as message

from django.contrib.auth.decorators import login_required

from django.shortcuts import get_object_or_404

from django.contrib.auth.hashers import make_password

from django.db.models.functions import Lower

from django.db.models.functions import Concat
from django.db.models import Q, CharField, Value as V

from datetime import datetime




# ------------------------------------------------------------------

from rest_framework import viewsets

from rest_framework.decorators import api_view

from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token



# -------------------------------------------------------------------
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.views.decorators.cache import cache_page
from django.core.cache import cache, caches


from reusable_functions.univesal.decorators import role_validator
from reusable_functions.univesal.string_manipulation import custom_html_wraper

# -------------------------------------------------------------------
from .filters import * #UserFilter

import locale
locale.setlocale(locale.LC_ALL, '') 

try:
    configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
    pagination_slice_leangth = configuration.pagination_slice_leangth
except Exception as e:
    HttpResponseRedirect('client_settings_page')


#--------------------------------------------------------------------
#   HTML PAGE
#--------------------------------------------------------------------

def login_page(request):
    return render(request, 'accounts/users/login_page.html')
@login_required
def manufacturers_page(request):
    return render(request, 'accounts/manufacturers_page.html')
@login_required
def suppliers_page(request):
    return render(request, 'accounts/suppliers_page.html')
@login_required
def customers_page(request):
    return render(request, 'accounts/customers_page.html')
@login_required
def users_page(request):
    return render(request, 'accounts/users_page.html')
@login_required
def client_settings_page(request):
    return render(request, 'accounts/client_settings_page.html')


#--------------------------------------------------------------------
#   //HTML PAGE
#--------------------------------------------------------------------




#--------------------------------------------------------------------
#   //AJAX
#--------------------------------------------------------------------

#   details
@login_required
@role_validator(['Data Analyst','Supervisor'])
def get_manufacturer_details(request):
    manufacturer_id = request.GET.get('manufacturer_id')

    manufacturer = Manufacturer.objects.get(id=int(manufacturer_id))
    company_name = manufacturer.company_name
    registration_number = manufacturer.registration_number
    phone_number = manufacturer.phone_number
    email = manufacturer.email
    address = manufacturer.address
    status = manufacturer.status
    if status == True:
        status = "True"
    else:
        status = "False"

    details = {
        "company_name": company_name,
        "registration_number": registration_number,
        "phone_number": phone_number,
        "email": email,
        "address": address,
        "status": status
    }
    return JsonResponse({'custome_status': "",'details': details})

@login_required
@role_validator(['Data Analyst','Supervisor'])
def get_customer_details(request):
    customer_id = request.GET.get('customer_id')

    customer = CustomerAccount.objects.get(id=int(customer_id))

    company_name = customer.company_name
    phone_number = customer.phone_number
    email = customer.email
    address = customer.address
    balance = customer.balance
    credit_limit = customer.credit_limit
    tin_number = customer.tin_number
    prz_number = customer.prz_number
    vat_number = customer.vat_number
    created_by = f"{ customer.created_by.first_name.title() } { customer.created_by.last_name.title() }"
    created_at = str(customer.created_at)[:10]
    updated_at = str(customer.updated_at)[:10]

    details = {
        'company_name': company_name,
        'phone_number': phone_number,
        'email': email,
        'address': custom_html_wraper(address),
        'balance': balance,
        'credit_limit': credit_limit,
        'tin_number': tin_number,
        'prz_number': prz_number,
        'vat_number': vat_number,
        'created_by': created_by,
        'created_at': created_at,
        'updated_at': updated_at
    }
    return JsonResponse({'custome_status': "",'details': details})









@login_required
@role_validator(['Data Analyst','Supervisor'])
def get_supplier_details(request):
    supplier_id = request.GET.get('supplier_id')

    supplier = Supplier.objects.get(id=int(supplier_id))
    company_name = supplier.company_name
    registration_number = supplier.registration_number
    phone_number = supplier.phone_number
    email = supplier.email
    address = supplier.address
    status = supplier.status
    if status == True:
        status = "True"
    else:
        status = "False"


    invoices = Invoice.objects.filter(supplier=supplier)
    total_invoices = invoices.count()
    total_paid = 0
    total_items = 0
    total_discount = 0
    total_cost = 0
    balance = 0
    for invoice in invoices:
        total_paid += float(invoice.total_paid)
        total_items += float(invoice.total_items)
        total_discount += float(invoice.total_discount)
        total_cost += float(invoice.total_cost)
        balance += float(invoice.balance) 

    # NOTE: consider refunds in calculating and displaying the values

    returns_out = ReturnOut.objects.filter(batch__invoice__supplier=supplier)
    total_returns_out = returns_out.count()


    details = {
        "company_name": company_name,
        "registration_number": registration_number,
        "phone_number": phone_number,
        "email": email,
        "address": address,
        "status": status,


        #financial
        "total_paid": total_paid,
        "total_discount": total_discount,
        "total_cost": total_cost,
        "balance": balance,
        # "":,

        #stock summery
        "total_invoices": total_invoices,
        "total_items_received": total_items,
        "total_returns_out": total_returns_out,
        "total_items_after_returns_out": total_items - total_returns_out
        # "":,
    }
    return JsonResponse({'custome_status': "",'details': details})



@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def get_configuration_details(request):
    configuration_id = request.GET.get('configuration_id')
    configuration = ClientSetting.objects.get(id=int(configuration_id))
    configuration_title = configuration.configuration_name
    company_registration = configuration.company_registration
    company_name = configuration.company_name
    phone_number = configuration.tel
    address = configuration.address
    email = configuration.email
    expiration_warning_days = configuration.expiration_warning
    status = configuration.status
    if status:
        status = "True"
    else:
        status = "False"
    terms_and_conditions = configuration.thank_you_message
    configuration_id = configuration.id

    details = {
        "configuration_title": configuration_title,
        "company_registration": company_registration,
        "company_name": company_name,
        "phone_number": phone_number,
        "address": address,
        "email": email,
        "expiration_warning_days": expiration_warning_days,
        "status": status,
        "configuration_id": configuration_id,
        "terms_and_conditions": terms_and_conditions
    }
    return JsonResponse({'custome_status': "",'details': details})

@login_required
@role_validator(['Data Analyst','Supervisor'])
def get_user_details(request):
    user_id = request.GET.get('user_id')
    user = User.objects.get(id=int(user_id))

    username = user.username
    first_name = user.first_name
    last_name = user.last_name
    email = user.email
    roles = user.roles
    phone_number = user.phone_number
    address = user.address
    date_joined = str(user.date_joined)[:10]
    last_login = str(user.last_login)[:10]
    if user.status == True:
        status = "True"
    else:
        status = "False"
    details = {
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "roles": roles,
        "phone_number": phone_number,
        "address": address,
        "status": status,
        "date_joined": date_joined,
        "last_login": last_login
    }
    return JsonResponse({'custome_status': "",'details': details})


#   update
@login_required
@role_validator(['Supervisor'])
def update_manufacturer(request):
    manufacturer_id = request.GET.get('manufacturer_id')
    manufacturer = Manufacturer.objects.get(id=int(manufacturer_id))

    company_name = request.GET.get('company_name')
    registration_number = request.GET.get('registration_number')
    phone_number = request.GET.get('phone_number')
    email = request.GET.get('email')
    address = request.GET.get('address')
    status = request.GET.get('status')

    already_exist = Manufacturer.objects.filter(company_name=company_name)
    if already_exist:
        if already_exist[0].id != int(manufacturer_id):
            return JsonResponse({'custome_status':"Error",'message':"Error, a manufacturer with the exact company name already_exists in the system"})

    else:
        old_manufacturer = manufacturer
        old_manufacturer.company_name = company_name
        old_manufacturer.registration_number = registration_number
        old_manufacturer.phone_number = phone_number
        old_manufacturer.email = email
        old_manufacturer.address = address
        old_manufacturer.created_by = request.user
        if status == "True":
            old_manufacturer.status = True
        else:
            old_manufacturer.status = False

        old_manufacturer.save()


    return JsonResponse({'custome_status':"",'message':"Manufacturer updated successfully!"})

@login_required
@role_validator(['Supervisor'])
def update_customer(request):  
    customer_id = request.GET.get('customer_id')
    customer = CustomerAccount.objects.get(id=int(customer_id))

    company_name = request.GET.get('company_name')
    phone_number = request.GET.get('phone_number')
    email = request.GET.get('email')
    address = request.GET.get('address')
    credit_limit = request.GET.get('credit_limit')
    tin_number = request.GET.get('tin_number')
    prz_number = request.GET.get('prz_number')
    vat_number = request.GET.get('vat_number')


    already_exist = CustomerAccount.objects.filter(company_name=company_name)
    if already_exist:
        if already_exist[0].id != int(customer_id):
            return JsonResponse({'custome_status':"Error",'message':"Error, a customer with the exact company name already_exists in the system"})

    else:
        old_customer = customer

        old_customer.company_name = company_name 
        old_customer.phone_number = phone_number 
        old_customer.email = email 
        old_customer.address = address 
        old_customer.credit_limit = credit_limit 
        old_customer.tin_number = tin_number 
        old_customer.prz_number = prz_number 
        old_customer.vat_number = vat_number 
        old_customer.created_by = created_by 

        old_customer.save()

    return JsonResponse({'custome_status':"",'message':"Customer account updated successfully!"})





@login_required
@role_validator(['Supervisor'])
def update_supplier(request):
    supplier_id = request.GET.get('supplier_id')
    supplier = Supplier.objects.get(id=int(supplier_id))

    company_name = request.GET.get('company_name')
    registration_number = request.GET.get('registration_number')
    phone_number = request.GET.get('phone_number')
    email = request.GET.get('email')
    address = request.GET.get('address')
    status = request.GET.get('status')

    already_exist = Supplier.objects.filter(company_name=company_name)
    if already_exist:
        if already_exist[0].id != int(supplier_id):
            return JsonResponse({'custome_status':"Error",'message':"Error, a supplier with the exact company name already_exists in the system"})

    else:
        old_supplier = supplier
        old_supplier.company_name = company_name
        old_supplier.registration_number = registration_number
        old_supplier.phone_number = phone_number
        old_supplier.email = email
        old_supplier.address = address
        old_supplier.created_by = request.user
        if status == "True":
            old_supplier.status = True
        else:
            old_supplier.status = False

        old_supplier.save()


    return JsonResponse({'custome_status':"",'message':"Supplier updated successfully!"})


@login_required
@role_validator(['Supervisor'])
def update_configuration(request):
    configuration_id = request.GET.get('configuration_id')
    configuration_title = request.GET.get('configuration_title')
    company_registration = request.GET.get('company_registration')
    company_name = request.GET.get('company_name')
    phone_number = request.GET.get('phone_number')
    address = request.GET.get('address')
    email = request.GET.get('email')
    expiration_warning_days = request.GET.get('expiration_warning_days')
    status = request.GET.get('status')
    terms_and_conditions = request.GET.get('terms_and_conditions')

    already_exist = ClientSetting.objects.filter(configuration_name=configuration_title)
    if already_exist:
        print(f"{ configuration_id }////////////////////////////////  {already_exist[0].id}")
        if int(already_exist[0].id) != int(configuration_id):
            return JsonResponse({'custome_status':"Error",'message':"A configuration with the same name already exist!"})
    
    old_configuration = ClientSetting.objects.get(id=int(configuration_id))
    
    old_configuration.configuration_name = configuration_title
    old_configuration.company_name = company_name
    old_configuration.address = address
    old_configuration.tel = phone_number
    old_configuration.company_registration = company_registration
    old_configuration.email = email
    old_configuration.thank_you_message = terms_and_conditions
    if status == "False":
        old_configuration.status = False
    else:
        old_configuration.status = True

    old_configuration.expiration_warning = expiration_warning_days
    old_configuration.created_by = request.user
    
    old_configuration.save() 
    return JsonResponse({'custome_status': "",'message': "Configuration updated successfully"})


@login_required
@role_validator(['Supervisor'])
def update_user(request):
    user_id = request.GET.get('user_id')
    user = User.objects.get(id=int(user_id))

    username = user.username
    first_name = request.GET.get('first_name')
    last_name = request.GET.get('last_name')
    email = request.GET.get('email')
    roles = request.GET.get('roles')
    phone_number = request.GET.get('phone_number')
    address = request.GET.get('address')
    status = request.GET.get('status')
    old_password = request.GET.get('old_password')
    new_password = request.GET.get('new_password')


    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.roles = roles
    user.phone_number = phone_number
    user.address = address
    user.status = status
    if old_password != "":
        #print("old not empty")
        if new_password != "":
            #print("new not empty")

            old_password_is_valid = authenticate(request, username=username, password=old_password)
            if old_password_is_valid is not None:
                #print(f"old valid {old_password_is_valid}")
                user.password = make_password(new_password)
            else:
                #print(f"old not valid {old_password_is_valid}")
                return JsonResponse({'custome_status':"Error",'message':"Error! Your old password is incorrect!"})

        else:
            #print("new  empty")

            return JsonResponse({'custome_status':"Error",'message':"Error! New password can not be empty if old password is not empty"})
    # user.old_password = old_password
    # user.new_password = new_password

    user.save()

    return JsonResponse({'custome_status':"",'message':"User updated successfully!"})


#   add
@login_required
def add_note(request):
    note_text = request.GET.get('note_text')
    new_note = Note()
    new_note.text = note_text
    new_note.created_by = request.user
    new_note.save()
    return JsonResponse({'custome_status':"",'message':"User updated successfully!"})



@login_required
@role_validator(['Supervisor'])
def add_configuration(request):
    configuration_title = request.GET.get('configuration_title')
    company_registration = request.GET.get('company_registration')
    company_name = request.GET.get('company_name')
    phone_number = request.GET.get('phone_number')
    address = request.GET.get('address')
    email = request.GET.get('email')
    expiration_warning_days = request.GET.get('expiration_warning_days')
    status = request.GET.get('status')
    terms_and_conditions = request.GET.get('terms_and_conditions')

    already_exist = ClientSetting.objects.filter(configuration_name=configuration_title)
    if already_exist:
        return JsonResponse({'custome_status':"Error",'message':"A configuration with the same name already exist!"})
    else:
        new_configuration = ClientSetting()
        
        new_configuration.configuration_name = configuration_title
        new_configuration.company_name = company_name
        new_configuration.address = address
        new_configuration.tel = phone_number
        new_configuration.company_registration = company_registration
        new_configuration.email = email
        new_configuration.thank_you_message = terms_and_conditions
        if status == "False":
            new_configuration.status = False
        new_configuration.expiration_warning = expiration_warning_days
        new_configuration.created_by = request.user
        
        new_configuration.save() 

    return JsonResponse({'custome_status':"",'message':"Configuration created successfully!"})


@login_required
@role_validator(['Supervisor'])
def add_user(request):
    username = request.GET.get('username')
    first_name = request.GET.get('first_name')
    last_name = request.GET.get('last_name')
    email = request.GET.get('email')
    roles = request.GET.get('roles')
    phone_number = request.GET.get('phone_number')
    address = request.GET.get('address')
    status = request.GET.get('status')
    password = request.GET.get('password')
    password1 = request.GET.get('password1')

    # print('ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc')
    # for user in User.objects.all():
    #     print(user.username)

    if password == password1:
        already_exist = User.objects.filter(username=username)
        # print('kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        # print(username)
        # print(already_exist)
        if already_exist:
            return JsonResponse({'custome_status':"Error",'message':"Another account already usese the same username! Please use a diffrent one"})
        else:
            try:
                new_user = User()
                new_user.username = username
                new_user.first_name = first_name
                new_user.last_name = last_name
                new_user.email = email
                new_user.roles = roles
                new_user.phone_number = phone_number
                new_user.address = address
                new_user.created_by = request.user
                new_user.status = False
                new_user.password = make_password(password)
                new_user.save()
                return JsonResponse({'custome_status':"",'message':"New user added successfully! This user need to be activated first"})
            except Exception as e:
                return JsonResponse({'custome_status':"Error",'message':str(e)})

    else:
        return JsonResponse({'custome_status':"Error",'message':"Your first password and the second one must match!"})


@login_required
@role_validator(['Supervisor'])
def add_manufacturer(request):
    company_name = request.GET.get('company_name')
    registration_number = request.GET.get('registration_number')
    phone_number = request.GET.get('phone_number')
    email = request.GET.get('email')
    address = request.GET.get('address')
    status = request.GET.get('status')

    already_exist = Manufacturer.objects.filter(company_name=company_name)
    if already_exist:
        return JsonResponse({'custome_status':"Error",'message':"Error, a manufacturer with the exact company name already_exists in the system"})

    else:
        new_manufacturer = Manufacturer()
        new_manufacturer.company_name = company_name
        new_manufacturer.registration_number = registration_number
        new_manufacturer.phone_number = phone_number
        new_manufacturer.email = email
        new_manufacturer.address = address
        new_manufacturer.created_by = request.user
        if status == "True":
            new_manufacturer.status = True
        else:
            new_manufacturer.status = False

        new_manufacturer.save()


    return JsonResponse({'custome_status':"",'message':"New manufacturer added successfully!"})






@login_required
@role_validator(['Supervisor'])
def add_customer(request):
    company_name = request.GET.get('company_name')
    registration_number = request.GET.get('registration_number')
    phone_number = request.GET.get('phone_number')
    email = request.GET.get('email')
    address = request.GET.get('address')
    status = request.GET.get('status')

    tin = request.GET.get('tin_number')
    prz = request.GET.get('prz_number')
    vat = request.GET.get('vat_number')

    already_exist = CustomerAccount.objects.filter(company_name=company_name)
    if already_exist:
        return JsonResponse({'custome_status':"Error",'message':"Error, a customer with the exact company name already_exists in the system"})

    else:
        new_customer = CustomerAccount()
        new_customer.company_name = company_name
        new_customer.registration_number = registration_number
        new_customer.phone_number = phone_number
        new_customer.email = email
        new_customer.address = address
        new_customer.tin_number = tin
        new_customer.prz_number = prz
        new_customer.vat_number = vat
        new_customer.created_by = request.user
        if status == "True":
            new_customer.status = True
        else:
            new_customer.status = False

        new_customer.save()


    return JsonResponse({'custome_status':"",'message':"New supplier added successfully!"})












@login_required
@role_validator(['Supervisor'])
def add_supplier(request):
    company_name = request.GET.get('company_name')
    registration_number = request.GET.get('registration_number')
    phone_number = request.GET.get('phone_number')
    email = request.GET.get('email')
    address = request.GET.get('address')
    status = request.GET.get('status')

    already_exist = Supplier.objects.filter(company_name=company_name)
    if already_exist:
        return JsonResponse({'custome_status':"Error",'message':"Error, a supplier with the exact company name already_exists in the system"})

    else:
        new_supplier = Supplier()
        new_supplier.company_name = company_name
        new_supplier.registration_number = registration_number
        new_supplier.phone_number = phone_number
        new_supplier.email = email
        new_supplier.address = address
        new_supplier.created_by = request.user
        if status == "True":
            new_supplier.status = True
        else:
            new_supplier.status = False

        new_supplier.save()


    return JsonResponse({'custome_status':"",'message':"New supplier added successfully!"})


# options


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def load_customer_options(request):
    search_query = request.GET.get('search_query')
    customers = CustomerAccount.objects.filter(company_name__icontains=search_query)[:6]

    title_option = f'<option value="all" selected>Customer Not Selected</option>'

    customer_options = [
    f"<option value='{customer.id}'>{customer.company_name}</option>" for customer in customers
    ]

    customer_options = [title_option] + customer_options

    return JsonResponse({'options': customer_options})


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def load_live_manufacturers_options(request):
    search_query = request.GET.get('search_text')
    manufacturers = Manufacturer.objects.filter(company_name__icontains=search_query)[:10]

    title_option = f'<option value="all" selected>Select Supplier (All)</option>'

    manufacturer_options = [
    f"<option value='{manufacturer.id}'>{manufacturer.company_name}</option>" for manufacturer in manufacturers
    ]

    manufacturer_options = [title_option] + manufacturer_options

    return JsonResponse({'options': manufacturer_options})

@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def load_live_suppliers_options(request):
    search_query = request.GET.get('search_text')
    suppliers = Supplier.objects.filter(company_name__icontains=search_query)[:10]

    title_option = f'<option value="all" selected>Select Supplier (All)</option>'

    supplier_options = [
    f"<option value='{supplier.id}'>{supplier.company_name}</option>" for supplier in suppliers
    ]

    supplier_options = [title_option] + supplier_options

    return JsonResponse({'options': supplier_options})


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def load_live_users_options(request):
    search_key = request.GET.get('search_text')
    # users = User.objects.filter(company_name__icontains=search_query)[:10]

    users = User.objects.annotate(
        full_text = Concat(
            'first_name', V(' '),'last_name', output_field=CharField()
            )
        ).filter(deleted=False, full_text__icontains=search_key).order_by('created_at')[:10]

    title_option = f'<option value="all" selected>Select User (All)</option>'

    user_options = [
    f"<option value='{user.id}'>{ user.first_name } { user.last_name }</option>" for user in users
    ]

    user_options = [title_option] + user_options

    return JsonResponse({'options': user_options})


#--------------------------------------------------------------------
#   //AJAX
#--------------------------------------------------------------------


@login_required
def home(request):
    current_year = datetime.now().year
    
    users = cache.get('___total_users')
    # message.success(request, 'Cache available')
    if users is None:
        # message.success(request, 'Cache Not available')
        users = User.objects.filter(deleted=False).count()
        cache.set('total_users', users)
        # message.success(request, 'Cache created')


    suppliers = cache.get('___total_suppliers')
    if suppliers is None:
        suppliers = Supplier.objects.filter(deleted=False).count()
        cache.set('total_suppliers', suppliers)


    batches = Batch.objects.filter(deleted=False).count()


    invoices = cache.get('___total_invoices')
    if invoices is None:
        invoices = Invoice.objects.filter(deleted=False, created_at__year=current_year).count()
        cache.set('total_invoices', invoices)
    batch_adjustments = cache.get('___total_batch_adjustments')
    if batch_adjustments is None:
        batch_adjustments = BatchAdjustment.objects.filter(created_at__year=current_year).count()
        cache.set('total_batch_adjustments', batch_adjustments)

    transactions = SaleTransaction.objects.filter(created_at__year=current_year).count()

    returns_inn = ReturnInn.objects.filter(created_at__year=current_year).count()

    #expenses
    expenses = Expense.objects.filter(created_at__year=current_year).count()



    #settings
    currencies = cache.get('___total_currencies')
    if currencies is None:
        currencies = PaymentMethod.objects.filter(deleted=False).count()
        cache.set('total_currencies', currencies)
    configurations = cache.get('___total_configurations')
    if configurations is None:
        configurations = ClientSetting.objects.filter(deleted=False).count()
        cache.set('total_configurations', configurations)
    expense_types = cache.get('___total_expense_types')
    if expense_types is None:
        expense_types = ExpensesType.objects.filter(active=True).count()
        cache.set('total_expense_types', expense_types)

    departments = Department.objects.all().count()
    categories = Category.objects.all().count()

    # utilities
    batch_adjustment_reasons = BatchAdjustmentReason.objects.all().count()
    return_reasons = ReturnReason.objects.all().count()
    payment_methods = PaymentMethod.objects.all().count()
    vat_codes = VATCode.objects.filter(deleted=False).count()
    new_alerts = Notification.objects.filter(status="New").count()



    #accounts
    manufacturers = cache.get('___total_manufacturers')
    if manufacturers is None:
        manufacturers = Manufacturer.objects.filter(deleted=False).count()
        #cache.set('total_manufacturers', manufacturers)
   
    sales = cache.get('___total_sales')
    if sales is None:
        sales = Sale.objects.filter(deleted=False, created_at__year=current_year).count()
        #cache.set('total_sales', sales)
    stocks = cache.get('___total_stocks')
    if stocks is None:
        stocks = Stock.objects.filter(deleted=False).count()
        #cache.set('total_stocks', stocks)
    products = cache.get('___total_products')
    if products is None:
        products = Product.objects.filter(deleted=False).count()
        #cache.set('total_products', products)
    returns_out = cache.get('___total_returns_out')
    if returns_out is None:
        returns_out = ReturnOut.objects.filter(deleted=False, created_at__year=current_year).count()

    customers = CustomerAccount.objects.filter(deleted=False).count()

    
    

    
    window_share_level = "1"
    context = {
        #settings
        'currencies':currencies,
        'configurations':configurations,
        'client_configurations': configurations,
        'expense_types':expense_types,
        'departments':departments,
        'categories':categories,

        #stock
        'batches':batches,
        'invoices':invoices,
        'batch_adjustments':batch_adjustments,
        'transactions':transactions,
        'returns_inn':returns_inn,

        #
        'expenses': expenses,

        # Utilities
        'batch_adjustment_reasons':batch_adjustment_reasons,
        'return_reasons':return_reasons,
        'payment_methods':payment_methods,
        'vat_codes':vat_codes,
        'new_alerts':new_alerts,



        #accounts
        'users':users,
        'suppliers':suppliers,
        'sales':sales,
        'manufacturers':manufacturers,
        'stocks':stocks,
        'stock':stocks,
        'products':products,
        'returns_out':returns_out,
        'customers':customers,

        

        ###
        'window_share_level':window_share_level,
        }



    try:
        user_roles_ = str(request.user.roles)
        #print(user_roles_)
        if user_roles_ == "Sales Rep":
            user_roles_ = 1
        elif user_roles_ == "Supervisor":
            user_roles_ = 2
        elif user_roles_ == "Data Analyst":
            user_roles_ = 3
        elif user_roles_ == "Supervisor, Sales Rep":
            user_roles_ = 4
        elif user_roles_ == "Data Analyst, Sales Rep":
            user_roles_ = 5
        elif user_roles_ == "Data Analyst, Supervisor":
            user_roles_ = 6
        elif user_roles_ == "Data Analyst, Supervisor, Sales Rep":
            user_roles_ = 7
        else:
            user_roles_ = ""
    except:
        user_roles_ = ""

    if user_roles_ == 1:
        return render(request, 'home/cashier_home.html', context)
    elif user_roles_ == 2:
        return render(request, 'home/supervisor_home.html', context)
    elif user_roles_ == 3:
        return render(request, 'home/data_analyst_home.html', context)
    elif user_roles_ == 4:
        return render(request, 'home/supervisor_cashier_home.html', context)
    elif user_roles_ == 5:
        return render(request, 'home/data_analyst_cashier_home.html', context)
    elif user_roles_ == 6:
        return render(request, 'home/data_analyst_supervisor_home.html', context)
    elif user_roles_ == 7:
        return render(request, 'home/data_analyst_supervisor_cashier_home.html', context)
    else:
        message.warning(request, f'This account: {request.user.username}, has no any previllages. Please login with a diffrent account.')
        return redirect("login")


#--------------------------------------------------------------------
#   DATA
#--------------------------------------------------------------------
@login_required
def suppliers_list(request):
    suppliers = Supplier.objects.filter(deleted=False).order_by('company_name')

    #filters
    try:
        company_name = request.GET['company_name']
        if company_name != '':
            suppliers = suppliers.filter(company_name__icontains=company_name)
    except:
        pass

    try:
        registration_number = request.GET['registration_number']
        if registration_number != '':
            suppliers = suppliers.filter(registration_number__icontains=registration_number)
    except:
        pass


    try:
        address = request.GET['address']
        if address != '':
            suppliers = suppliers.filter(address__icontains=address)
    except:
        pass



    data = list(suppliers.values())

    print(data)
    return JsonResponse(data, safe=False) 



#--------------------------------------------------------------------
#AUTHENTICATION
#--------------------------------------------------------------------
@login_required
def user_logout(request):
    logout(request)
    return redirect("home")




def login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            built_inn_login_function(request, user)
            remove_nav ='False'
            username = username.title()
            message = f"You are now logged in as {username}"
            return redirect("home")
        else:
            message = "Invalid username or password!"
            return JsonResponse({'custome_status': "Error", 'message':message})
    else:
        return redirect('login_page')



# -------------------------------------------------------------------------------
# AJAX ==========================================================================
# -------------------------------------------------------------------------------



#   delete
@login_required
def delete_note(request):
    note_id = request.GET.get('note_id')
    note = Note.objects.get(id=int(note_id))
    note.deleted = True
    note.save()
    return JsonResponse({'message':"Note deleted successfully!"})



#   listing
@login_required
def ajax_notes_live_search(request):
    notes_ = Note.objects.filter(created_by=request.user, deleted=False).order_by('-created_at')[:50]
    notes = reversed(notes_)
    notes_list = ''

    for note in notes:
        item = f"""
            <tr>
                <td style="width: 15%;">{ note.created_at: %d %B %Y }</td>
                <td style="width: 80%;">{ note.text}</td>
                <td style="width: 5%;"><button onclick="deleteNote({ note.id })"><i class="notika-icon notika-trash" style="color: red;"></i></button></td>
            </tr>
            <tr>
                <td colspan="3">
                    <hr>
                </td>
            </tr>
        """
        notes_list += item

    return JsonResponse({'notes_list':notes_list})


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_configurations_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        configurations = ClientSetting.objects.filter(deleted=False)


    if request_type == "FORM-FILTER":
        # form filterr here
        configurations = ClientSetting.objects.filter(deleted=False)

    
    #------------------------------------------------------------------------------ 
    data_queryset = configurations
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
                <th>Configuration Title</th>
                <th>Company Name</th>
                <th>Address</th>
                <th>Tel</th>
                <th>Active</th>
                <th colspan="2">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for configuration in data_page:
        row = f"""
            <tr>
                <th>{ configuration.configuration_name }</th>
                <td>{ configuration.company_name } </td>
                <td>{ configuration.address } </td>
                <td>{ configuration.tel } </td>
                <td>{ configuration.status } </td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ configuration.id }" type="button"  data-toggle="modal" data-target="#configurationDetailsModal" id="configuration-details-modal-button"><i class="notika-icon notika-menus"></a></td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ configuration.id }" type="button"  data-toggle="modal" data-target="#updateConfigurationModal" id="edit-configuration-modal-button"><i class="notika-icon notika-edit"></a></td>

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


    table_summery = f" {configurations.count()} out of {ClientSetting.objects.all().count()} configurations."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})




@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_suppliers_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        suppliers = Supplier.objects.filter(deleted=False).order_by(Lower('company_name'))


    if request_type == "FORM-FILTER":
        # form filterr here
        suppliers = Supplier.objects.filter(deleted=False).order_by(Lower('company_name'))

    
    #------------------------------------------------------------------------------ 
    data_queryset = suppliers
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
                <th>Company Name</th>
                <th>Registration Number</th>
                <th>Phone</th>
                <th>Email</th>
                <th>Address</th>
                <th colspan="2">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for supplier in data_page:
        row = f"""
            <tr>
                <th>{ supplier.company_name } </th>
                <td>{ supplier.registration_number } </td>
                <td>{ supplier.phone_number }</td>
                <td>{ supplier.email }</td>
                <td style="width:20%">{ supplier.address }</td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ supplier.id }" type="button"  data-toggle="modal" data-target="#supplierDetailsModal" id="supplier-details-modal-button"><i class="notika-icon notika-menus"></a></td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ supplier.id }" type="button"  data-toggle="modal" data-target="#updateSupplierModal" id="update-supplier-modal-button"><i class="notika-icon notika-edit"></a></td>

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


    table_summery = f" {suppliers.count()} out of {Supplier.objects.all().count()} suppliers."
    print(f"DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD: {str(data_page)}")
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})

@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_customers_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        customers = CustomerAccount.objects.filter(deleted=False)


    if request_type == "FORM-FILTER":
        # form filterr here
        customers = CustomerAccount.objects.filter(deleted=False)

    
    #------------------------------------------------------------------------------ 
    data_queryset = customers
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
                <th>Company Name</th>
                <th>Phone</th>
                <th style="text-align: right;">Balance</th>
                <th style="text-align: right;">Credit Limit</th>
                <th>Added by</th>
                <th>Created on</th>
                <th>Last Update</th>
                <th colspan="2">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for customer in data_page:
        row = f"""
            <tr>
                <th>{ customer.company_name } </th>
                <td>{ customer.phone_number } </td>
                <td style="text-align: right;">{ locale.format_string('%.2f', customer.balance, grouping=True) } </td>
                <td style="text-align: right;">{ locale.format_string('%.2f', customer.credit_limit, grouping=True) } </td>
                <td>{ customer.created_by.first_name.title() } { customer.created_by.last_name.title() }</td>
                <td>{ str(customer.created_at)[:10] }</td>
                <td>{ str(customer.updated_at)[:10] }</td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ customer.id }" type="button"  data-toggle="modal" data-target="#customerDetailsModal" id="configuration-details-modal-button"><i class="notika-icon notika-menus"></a></td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ customer.id }" type="button"  data-toggle="modal" data-target="#updateCustomerModal" id="update-customer-details-modal-button"><i class="notika-icon notika-edit"></a></td>
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


    table_summery = f" {customers.count()} out of {CustomerAccount.objects.all().count()} customers."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})



@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_manufacturers_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        manufacturers = Manufacturer.objects.filter(deleted=False)


    if request_type == "FORM-FILTER":
        # form filterr here
        manufacturers = Manufacturer.objects.filter(deleted=False)

    
    #------------------------------------------------------------------------------ 
    data_queryset = manufacturers
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
                <th>Company Name</th>
                <th>Registration Number</th>
                <th>Phone</th>
                <th>Email</th>
                <th>Address</th>
                <th colspan="2">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for manufacturer in data_page:
        row = f"""
            <tr>
                <th>{ manufacturer.company_name } </th>
                <td>{ manufacturer.registration_number } </td>
                <td>{ manufacturer.phone_number }</td>
                <td>{ manufacturer.email }</td>
                <td>{ manufacturer.address }</td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ manufacturer.id }" type="button"  data-toggle="modal" data-target="#manufacturerDetailsModal" id="configuration-details-modal-button"><i class="notika-icon notika-menus"></a></td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ manufacturer.id }" type="button"  data-toggle="modal" data-target="#updateManufacturerModal" id="update-manufacturer-details-modal-button"><i class="notika-icon notika-edit"></a></td>
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


    table_summery = f" {manufacturers.count()} out of {Manufacturer.objects.all().count()} manufacturers."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})



def new_users_list_f(request):
    filtered_users = UserFilter(
        request.GET,
        queryset = User.objects.all()
    )
    paginated_filtered_users = Paginator(filtered_users.qs, 2)
    page_number = request.GET.get('page')
    users_page_obj = paginated_filtered_users.get_page(page_number)
    context = {
        'filtered_users': filtered_users,
        'users_page_obj': users_page_obj,
    }

    return render(request, 'test/test1.html', context)



@login_required
@role_validator(['Data Analyst','Supervisor'])
def ajax_users_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        users = User.objects.filter(deleted=False).exclude(is_superuser=True)


    if request_type == "FORM-FILTER":
        # form filterr here
        users = User.objects.filter(deleted=False).exclude(is_superuser=True)

    
    #------------------------------------------------------------------------------ 
    data_queryset = users
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
                <th>Name</th>
                <th>Employee ID / Username</th>
                <th>Role</th>
                <th>Phone</th>
                <th>Active</th>
                <th colspan="2">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for user in data_page:
        row = f"""
            <tr>
                <td>{ user.first_name.title() } { user.last_name.title() }</td>
                <td>{ user.username }</td>
                <td>{ user.roles }</td>
                <td>{ user.phone_number }</td>
                <td>{ user.status }</td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ user.id }" type="button"  data-toggle="modal" data-target="#userDetailsModal" id="return-out-details-modal-button"><i class="notika-icon notika-menus"></a></td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ user.id }" type="button"  data-toggle="modal" data-target="#updateUserModal" id="return-out-details-modal-button"><i class="notika-icon notika-edit"></a></td>
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


    table_summery = f" {users.count()} out of {User.objects.all().count()} users."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})


