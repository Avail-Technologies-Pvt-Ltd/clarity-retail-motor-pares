from django.shortcuts import render
from .models import *

from dateutil.relativedelta import relativedelta
from datetime import datetime as datetime_

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, FileResponse

from django.contrib.auth.hashers import make_password
import hashlib
import os
from django.conf import settings

from accounts.models import Branch, User, ClientSetting, PrinterCase



def system_settings(request):
    context = {}
    
    # User Profile Data
    if request.user.is_authenticated:
        context['user'] = request.user
    
    # LOCAL BRANCH - get the branch marked as is_local=True
    local_branch = Branch.objects.filter(is_local=True).first()
    context['branch'] = local_branch
    
    # Client Settings Data
    client_setting = ClientSetting.objects.filter(deleted=False).first() if hasattr(ClientSetting, 'deleted') else ClientSetting.objects.first()
    context['client_setting'] = client_setting
    
    # PRINTERS - Get ALL printers (not filtered by branch)
    # Your PrinterCase model doesn't have a branch relationship, so get all
    if hasattr(PrinterCase, 'deleted'):
        printers = PrinterCase.objects.filter(deleted=False)
    else:
        printers = PrinterCase.objects.all()
    context['printers'] = printers
    
    # Subscription Data
    try:
        last_subscription = SubscriptionPayment.objects.all().order_by('-created_at').first()
        if last_subscription:
            context['subscription_status'] = {
                'expiration_date': str(last_subscription.date_to)[:10] if last_subscription.date_to else "N/A",
                'date': str(last_subscription.created_at)[:10] if last_subscription.created_at else "N/A",
                'active_date': str(last_subscription.date_from)[:10] if last_subscription.date_from else "N/A",
                'duration': last_subscription.duration,
            }
        else:
            context['subscription_status'] = {
                'expiration_date': "N/A",
                'date': "N/A",
                'active_date': "N/A",
                'duration': "N/A",
            }
        
        context['old_payments'] = SubscriptionPayment.objects.all().order_by('-created_at')
        
        order_profile = OrderProfile.objects.all().first()
        if order_profile:
            context['payment_instructions'] = order_profile.payment_instructions
            context['contact'] = {
                'whatsapp': getattr(order_profile, 'whatsapp', 'N/A'),
                'call': getattr(order_profile, 'call', 'N/A'),
                'email': getattr(order_profile, 'email', 'N/A'),
                'website': getattr(order_profile, 'website', 'N/A'),
            }
    except Exception as e:
        context['subscription_status'] = {
            'expiration_date': "N/A",
            'date': "N/A",
            'active_date': "N/A",
            'duration': "N/A",
        }
        context['old_payments'] = []
    
    return render(request, 'order/system_settings/system_settings.html', context)


def api_create_branch(request):
    """Create a new local branch"""
    if request.method in ['GET', 'POST']:
        try:
            if request.GET:
                data = request.GET
            else:
                data = request.POST
            
            # Check if a local branch already exists
            existing_local = Branch.objects.filter(is_local=True).first()
            if existing_local:
                return JsonResponse({'custome_status': 'Error', 'message': 'A local branch already exists. Please edit it instead.'})
            
            branch = Branch()
            branch.is_local = True
            branch.branch_name = data.get('branch_name', '')
            branch.manager = data.get('manager', '')
            branch.phone = data.get('phone', '')
            branch.email = data.get('email', '')
            branch.address = data.get('address', '')
            branch.city = data.get('city', '')
            branch.country = data.get('country', 'ZW')
            branch.type = data.get('type', 'STORE')
            branch.is_active = True
            branch.save()
            
            return JsonResponse({'custome_status': 'Success', 'message': 'Local branch created successfully!'})
        except Exception as e:
            return JsonResponse({'custome_status': 'Error', 'message': str(e)})
    return JsonResponse({'custome_status': 'Error', 'message': 'Invalid request method'})


def api_update_branch(request):
    """Update LOCAL branch via AJAX"""
    if request.method in ['GET', 'POST']:
        try:
            if request.GET:
                data = request.GET
            else:
                data = request.POST
            
            # Get the local branch (marked as is_local=True)
            branch = Branch.objects.filter(is_local=True).first()
            if not branch:
                # If no local branch exists, create one
                branch = Branch()
                branch.is_local = True
            
            # Update all editable fields
            branch.branch_name = data.get('branch_name', branch.branch_name)
            branch.manager = data.get('manager', branch.manager)
            branch.phone = data.get('phone', branch.phone)
            branch.email = data.get('email', branch.email)
            branch.address = data.get('address', branch.address)
            branch.city = data.get('city', branch.city)
            branch.country = data.get('country', 'ZW')
            branch.type = data.get('type', branch.type)
            branch.sync_url = data.get('sync_url', branch.sync_url)
            branch.is_active = data.get('is_active', 'true') == 'true'
            branch.save()
            
            return JsonResponse({'custome_status': 'Success', 'message': 'Local branch updated successfully!'})
        except Exception as e:
            return JsonResponse({'custome_status': 'Error', 'message': str(e)})
    return JsonResponse({'custome_status': 'Error', 'message': 'Invalid request method'})



def api_delete_printer(request):
    """Delete printer configuration via AJAX"""
    if request.method in ['GET', 'POST']:
        try:
            if request.GET:
                printer_id = request.GET.get('printer_id')
            else:
                printer_id = request.POST.get('printer_id')
            
            if printer_id:
                printer = PrinterCase.objects.get(id=printer_id)
                # Soft delete if deleted field exists, otherwise hard delete
                if hasattr(printer, 'deleted'):
                    printer.deleted = True
                    printer.save()
                else:
                    printer.delete()
                return JsonResponse({'custome_status': 'Success', 'message': 'Printer deleted successfully!'})
            else:
                return JsonResponse({'custome_status': 'Error', 'message': 'Printer ID not provided'})
        except PrinterCase.DoesNotExist:
            return JsonResponse({'custome_status': 'Error', 'message': 'Printer not found'})
        except Exception as e:
            return JsonResponse({'custome_status': 'Error', 'message': str(e)})
    return JsonResponse({'custome_status': 'Error', 'message': 'Invalid request method'})








def create_backup(request):
    from django.http import FileResponse
    return FileResponse(open('db.sqlite3', 'rb'))


#	html
def add_subscription_page(request):
    recent_state = 'ENTER SUBSCRIPTION KEY HERE'
    if request.method == "POST":
        key = request.POST.get('key')

        today = str(datetime_.today().date())[:10]

        order_profile = OrderProfile.objects.all().first()

        monthly_keys_list = order_profile.monthly_keys.rstrip(",").split(",")
        anual_keys_list = order_profile.anual_keys.rstrip(",").split(",")
        

        if key != "":
            vx = make_password
            key = hashlib.sha256(key.encode('utf-8')).digest().hex()
            print(key)

            if key in monthly_keys_list:

                new_payment = SubscriptionPayment()
                new_payment.duration = "1 month"
                try:
                    last_subscription = SubscriptionPayment.objects.all().order_by('created_at').last() 
                    new_payment.date_from = last_subscription.date_to + relativedelta(days=1)
                    new_payment.date_to = last_subscription.date_to + relativedelta(months=1)
                except:
                    new_payment.date_from = today + relativedelta(days=1)
                    new_payment.date_to = today + relativedelta(months=1)

                new_payment.subscription_key = key
                new_payment.created_by = request.user
                new_payment.save()

                new_list = ''
                for i in monthly_keys_list:
                    if i != key:
                        new_list = new_list + f'{ i },'
                order_profile.monthly_keys = new_list
                order_profile.save()
                recent_state = "SUBSCRIPTION SUCCESSFUL"


            elif key in anual_keys_list:

                new_payment = SubscriptionPayment()
                new_payment.duration = "1 year"
                try:
                    last_subscription = SubscriptionPayment.objects.all().order_by('created_at').last() 
                    new_payment.date_from = last_subscription.date_to + relativedelta(days=1)
                    new_payment.date_to = last_subscription.date_to + relativedelta(years=1)
                except:
                    new_payment.date_from = today + relativedelta(days=1)
                    new_payment.date_to = today + relativedelta(years=1)

                new_payment.subscription_key = key
                new_payment.created_by = request.user
                new_payment.save()

                new_list = ''
                for i in anual_keys_list:
                    if i != key:
                        new_list = new_list + f'{ i },'
                order_profile.anual_keys = new_list
                order_profile.save()
                recent_state = "SUBSCRIPTION SUCCESSFUL"
            else:
                recent_state = "INVALID KEY"
            


    try:
        last_subscription = SubscriptionPayment.objects.all().order_by('created_at').last()
        order_profile = OrderProfile.objects.all().first()

        # time_left = order_profile.time_left
        expiration_date = last_subscription.date_to
        date = last_subscription.created_at
        active_date = last_subscription.date_from
        duration = last_subscription.duration
    except:
        # time_left = "N/A"
        expiration_date = "N/A"
        date = "N/A"
        active_date = "N/A"
        duration = "N/A"


    try:
        order_profile = OrderProfile.objects.all().first()

        whatsapp = order_profile.whatsapp
        call = order_profile.call
        email = order_profile.email
        website = order_profile.website
    except:
        whatsapp = "N/A"
        call = "N/A"
        email = "N/A"
        website = "N/A"



    contact = {
        'whatsapp': whatsapp,
        'call': call,
        'email': email,
        'website': website,
    }

    subscription_status = {
        'expiration_date': str(expiration_date)[:10],
        'date': str(date)[:10],
        'active_date': str(active_date)[:10],
        'duration': duration,
    }

    old_payments = SubscriptionPayment.objects.all().order_by('created_at').reverse()
    payment_instructions = order_profile.payment_instructions

    context = {
        'subscription_status': subscription_status,
        'contact': contact,
        'recent_state': recent_state,
        'old_payments': old_payments,
        'payment_instructions': payment_instructions,
    }
    return render(request, 'order/subscriptions/add_subscription_page.html', context)


# HELPER FUNCTIONS

# GLOBAL SEARCH
def load_global_search_options(request):
    search_query = request.GET.get('search_query')

    features = [
    # key_words, link, name, discription
        { }
    ]
    links = [
        f"<option value='{ feature['link'] }'> { feature['name'] }, <small>{ feature['description'] }</small> </option>" for feature in features
    ]

    return JsonResponse({'options':links})


# API
def days_from_now(request):
    days = request.GET.get('days')
    today = datetime_.today().date()
    new_date = today + relativedelta(days=int(days))
    return JsonResponse({'new_date': new_date})


# DIRECT PYTHON CALL
def days_from_now_python(days):
    today = datetime_.today().date()
    new_date = today + relativedelta(days=int(days))
    return new_date


# ============================================
# ADDITIONAL API ENDPOINTS FOR SYSTEM SETTINGS
# ============================================

def api_update_user_profile(request):
    """Update user profile via AJAX"""
    if request.method in ['GET', 'POST']:
        try:
            user = request.user
            if request.GET:
                data = request.GET
            else:
                data = request.POST
            
            user.username = data.get('username', user.username)
            user.email = data.get('email', user.email)
            if hasattr(user, 'phone_number'):
                user.phone_number = data.get('phone_number', getattr(user, 'phone_number', ''))
            if hasattr(user, 'address'):
                user.address = data.get('address', getattr(user, 'address', ''))
            if hasattr(user, 'roles'):
                user.roles = data.get('roles', getattr(user, 'roles', 'Sales Rep'))
            if hasattr(user, 'status'):
                user.status = data.get('status', 'true') == 'true'
            if hasattr(user, 'e_signature_link'):
                user.e_signature_link = data.get('e_signature_link', getattr(user, 'e_signature_link', ''))
            
            user.save()
            return JsonResponse({'custome_status': 'Success', 'message': 'User profile updated successfully!'})
        except Exception as e:
            return JsonResponse({'custome_status': 'Error', 'message': str(e)})
    return JsonResponse({'custome_status': 'Error', 'message': 'Invalid request method'})




def api_update_client_setting(request):
    """Update client settings via AJAX"""
    if request.method in ['GET', 'POST']:
        try:
            if request.GET:
                data = request.GET
            else:
                data = request.POST
            
            client_setting = ClientSetting.objects.first()
            if not client_setting:
                client_setting = ClientSetting()
                client_setting.created_by = request.user
            
            client_setting.configuration_name = data.get('configuration_name', 'DefaultConfig')
            client_setting.company_name = data.get('company_name', '')
            client_setting.address = data.get('address', '')
            client_setting.tel = data.get('tel', '')
            client_setting.tin_number = data.get('tin_number', '')
            client_setting.prz_number = data.get('prz_number', '')
            client_setting.vat_number = data.get('vat_number', '')
            client_setting.invoice_number_prefix = data.get('invoice_number_prefix', 'INV-')
            client_setting.bank_1_bank_name = data.get('bank_1_bank_name', '')
            client_setting.bank_1_account_name = data.get('bank_1_account_name', '')
            client_setting.thank_you_message = data.get('thank_you_message', '')
            client_setting.email = data.get('email', '')
            client_setting.company_registration = data.get('company_registration', '')
            client_setting.save()
            
            return JsonResponse({'custome_status': 'Success', 'message': 'Client settings updated successfully!'})
        except Exception as e:
            return JsonResponse({'custome_status': 'Error', 'message': str(e)})
    return JsonResponse({'custome_status': 'Error', 'message': 'Invalid request method'})


def api_update_printer(request):
    """Update printer configuration via AJAX"""
    if request.method in ['GET', 'POST']:
        try:
            if request.GET:
                data = request.GET
            else:
                data = request.POST
            
            printer_id = data.get('printer_id')
            if printer_id:
                printer = PrinterCase.objects.get(id=printer_id)
            else:
                printer = PrinterCase()
                printer.created_by = request.user
            
            printer.printer_name = data.get('printer_name', '')
            printer.client_node = data.get('client_node', '')
            printer.status = data.get('status', 'true') == 'true'
            printer.save()
            
            return JsonResponse({'custome_status': 'Success', 'message': 'Printer configuration saved successfully!'})
        except Exception as e:
            return JsonResponse({'custome_status': 'Error', 'message': str(e)})
    return JsonResponse({'custome_status': 'Error', 'message': 'Invalid request method'})


def api_activate_subscription(request):
    """Activate subscription key via AJAX - uses your existing logic"""
    if request.method in ['GET', 'POST']:
        try:
            if request.GET:
                key = request.GET.get('subscription_key')
            else:
                key = request.POST.get('subscription_key')
            
            today = str(datetime_.today().date())[:10]
            order_profile = OrderProfile.objects.all().first()
            
            if not order_profile:
                return JsonResponse({'custome_status': 'Error', 'message': 'Order profile not found'})
            
            monthly_keys_list = order_profile.monthly_keys.rstrip(",").split(",") if order_profile.monthly_keys else []
            anual_keys_list = order_profile.anual_keys.rstrip(",").split(",") if order_profile.anual_keys else []
            
            if key:
                key_hash = hashlib.sha256(key.encode('utf-8')).digest().hex()
                
                if key_hash in monthly_keys_list:
                    new_payment = SubscriptionPayment()
                    new_payment.duration = "1 month"
                    try:
                        last_subscription = SubscriptionPayment.objects.all().order_by('created_at').last()
                        new_payment.date_from = last_subscription.date_to + relativedelta(days=1)
                        new_payment.date_to = last_subscription.date_to + relativedelta(months=1)
                    except:
                        new_payment.date_from = datetime_.today().date()
                        new_payment.date_to = datetime_.today().date() + relativedelta(months=1)
                    
                    new_payment.subscription_key = key_hash
                    new_payment.created_by = request.user
                    new_payment.save()
                    
                    new_list = ','.join([i for i in monthly_keys_list if i != key_hash])
                    order_profile.monthly_keys = new_list + (',' if new_list else '')
                    order_profile.save()
                    
                    return JsonResponse({'custome_status': 'Success', 'message': 'Monthly subscription activated successfully!'})
                
                elif key_hash in anual_keys_list:
                    new_payment = SubscriptionPayment()
                    new_payment.duration = "1 year"
                    try:
                        last_subscription = SubscriptionPayment.objects.all().order_by('created_at').last()
                        new_payment.date_from = last_subscription.date_to + relativedelta(days=1)
                        new_payment.date_to = last_subscription.date_to + relativedelta(years=1)
                    except:
                        new_payment.date_from = datetime_.today().date()
                        new_payment.date_to = datetime_.today().date() + relativedelta(years=1)
                    
                    new_payment.subscription_key = key_hash
                    new_payment.created_by = request.user
                    new_payment.save()
                    
                    new_list = ','.join([i for i in anual_keys_list if i != key_hash])
                    order_profile.anual_keys = new_list + (',' if new_list else '')
                    order_profile.save()
                    
                    return JsonResponse({'custome_status': 'Success', 'message': 'Annual subscription activated successfully!'})
                else:
                    return JsonResponse({'custome_status': 'Error', 'message': 'Invalid subscription key'})
            else:
                return JsonResponse({'custome_status': 'Error', 'message': 'Please provide a subscription key'})
        except Exception as e:
            return JsonResponse({'custome_status': 'Error', 'message': str(e)})
    return JsonResponse({'custome_status': 'Error', 'message': 'Invalid request method'})


def api_get_update_log(request):
    """Read updates.txt file from root folder and return content"""
    updates_file_path = os.path.join(settings.BASE_DIR, 'updates.txt')
    if os.path.exists(updates_file_path):
        with open(updates_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return JsonResponse({'custome_status': 'Success', 'content': content})
    else:
        return JsonResponse({'custome_status': 'Error', 'message': 'updates.txt not found in root directory'})