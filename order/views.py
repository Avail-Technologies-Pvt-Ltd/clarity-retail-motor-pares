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
from order.models import SyncManager, SubscriptionPayment




# NEW SETTINGS

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

def activate_subscription(request):
    if request.method == "POST":
        return JsonResponse({
            'title': "Sim subscription",
            'icon': "success", 
            'text': "Note: this feature is not yet functional"
        })

    return JsonResponse({
        'title': "Error",
        'icon': "error", 
        'text': str(e)
    }, status=400)


@require_POST
def update_notification_settings(request):
    try:
        hosting_email = request.POST.get('hosting_email')
        hosting_email_password = request.POST.get('hosting_email_password')
        notification_receiving_emails = request.POST.get('notification_receiving_emails')
        stock_expiration_warning_days = request.POST.get('stock_expiration_warning_days')

        # Parse the JSON string to list
        try:
            email_list = json.loads(notification_receiving_emails) if notification_receiving_emails else []
        except json.JSONDecodeError:
            email_list = []

        # Update or create ClientSetting
        client_settings = ClientSetting.objects.filter(status=True)
        if client_settings:
            client_setting = client_settings.first()
            client_setting.hosting_email = hosting_email
            client_setting.hosting_email_password = hosting_email_password
            client_setting.notification_receiving_emails = email_list  # Store as list
            client_setting.expiration_warning = stock_expiration_warning_days
            client_setting.created_by = request.user
            client_setting.save()
        else:
            client_setting = ClientSetting()
            client_setting.hosting_email = hosting_email
            client_setting.hosting_email_password = hosting_email_password
            client_setting.notification_receiving_emails = email_list  # Store as list
            client_setting.expiration_warning = stock_expiration_warning_days
            client_setting.created_by = request.user
            client_setting.save()

        # Update or create NotificationsManager
        notifications_managers = NotificationsManager.objects.all()
        if notifications_managers:
            notifications_manager = notifications_managers.first()
            notifications_manager.hosting_email = hosting_email 
            notifications_manager.hosting_email_password = hosting_email_password 
            notifications_manager.notification_receiving_emails = email_list  # Store as list
            notifications_manager.stock_expiration_warning_days = stock_expiration_warning_days 
            notifications_manager.created_by = request.user 
            notifications_manager.save() 
        else:
            notifications_manager = NotificationsManager()
            notifications_manager.hosting_email = hosting_email 
            notifications_manager.hosting_email_password = hosting_email_password 
            notifications_manager.notification_receiving_emails = email_list  # Store as list
            notifications_manager.stock_expiration_warning_days = stock_expiration_warning_days 
            notifications_manager.created_by = request.user 
            notifications_manager.save() 

        return JsonResponse({
            'title': "Saved",
            'icon': "success", 
            'text': "Notification settings applied successfully!"
        })

    except Exception as e:
        return JsonResponse({
            'title': "Error",
            'icon': "error", 
            'text': str(e)
        }, status=400)


def update_sync_settings(request):
    if request.method == "POST":
        sync_url = request.POST.get('sync_url')
        sync_intervals_minutes = request.POST.get('sync_intervals_minutes')

        sync_managers = SyncManager.objects.all()
        if sync_managers:
            sync_manager = sync_managers.first()
            sync_manager.sync_url = sync_url
            sync_manager.sync_intervals_minutes = sync_intervals_minutes
            sync_manager.created_by = request.user
            sync_manager.save()

        else:
            sync_manager = SyncManager()
            sync_manager.sync_url = sync_url
            sync_manager.sync_intervals_minutes = sync_intervals_minutes
            sync_manager.created_by = request.user
            sync_manager.save()

        return JsonResponse({
            'title': "Saved",
            'icon': "success", 
            'text': "Data sysnc settings applied successfully!"
        })

    return JsonResponse({'error': 'Invalid request method'}, status=400)


# ================================================================================



def system_settings(request):
    context = {}
    
    # User Profile Data
    if request.user.is_authenticated:
        context['user'] = request.user
    
    # LOCAL BRANCH - get the branch marked as is_local=True
    local_branch = Branch.objects.filter(is_local=True)
    if local_branch:
        context['branch'] = local_branch.first()
    
    # Client Settings Data
    client_setting = ClientSetting.objects.filter(status=True)
    if client_setting:
        context['client_setting'] = client_setting.first()

    sync_manager = SyncManager.objects.all()
    if sync_manager:
        context['sync_manager'] = sync_manager.first()

    notifications_manager = NotificationsManager.objects.all()
    if notifications_manager:
        context['notifications_manager'] = notifications_manager.first()

    subscription_payments = SubscriptionPayment.objects.all()
    if subscription_payments:
        context['subscription_payments'] = subscription_payments


    subscription_manager = SubscriptionManager.objects.first()
    
    # Format instructions
    if subscription_manager and subscription_manager.instructions:
        formatted_instructions = []
        for line in subscription_manager.instructions.splitlines():
            line = line.strip()
            if line.startswith('---'):
                formatted_instructions.append({'type': 'divider'})
            elif line.startswith('--'):
                formatted_instructions.append({'type': 'subheading', 'text': line[2:].strip()})
            elif line.startswith('-'):
                formatted_instructions.append({'type': 'bullet', 'text': line[1:].strip()})
            elif line:
                formatted_instructions.append({'type': 'text', 'text': line})
            else:
                formatted_instructions.append({'type': 'break'})
    else:
        formatted_instructions = None
    
    context['formatted_instructions'] = formatted_instructions
    
    # PRINTERS - Get ALL printers (not filtered by branch)
    # Your PrinterCase model doesn't have a branch relationship, so get all
    if hasattr(PrinterCase, 'deleted'):
        printers = PrinterCase.objects.filter(deleted=False)
    else:
        printers = PrinterCase.objects.all()
    context['printers'] = printers
    

    
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

        order_profile = SubscriptionManager.objects.all().first()

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
        order_profile = SubscriptionManager.objects.all().first()

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
        order_profile = SubscriptionManager.objects.all().first()

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

from django.http import JsonResponse
from django.urls import reverse
import json


def load_all_search_features(request):
    """
    Load all searchable features at once for client-side caching
    """
    try:
        # Build your features list
        
        features = [
            # DASHBOARD & QUICK ACCESS
            {
                'name': 'Dashboard',
                'description': 'Main overview and analytics',
                'link': reverse('home'),
                'icon': 'notika-icon notika-home',
                'category': 'Dashboard',
                'keywords': ['dashboard', 'home', 'overview', 'analytics'],
                'badge': None
            },
            {
                'name': 'P.O.S',
                'description': 'Point of Sale - Quick checkout',
                'link': reverse('pos'),
                'icon': 'notika-icon notika-cart',
                'category': 'Dashboard',
                'keywords': ['pos', 'point of sale', 'checkout', 'register'],
                'badge': None
            },
            {
                'name': 'Alerts',
                'description': 'View recent notifications and updates',
                'link': reverse('notifications_page'),
                'icon': 'notika-icon notika-alarm',
                'category': 'Dashboard',
                'keywords': ['alerts', 'notifications', 'updates', 'messages', 'unread'],
                'badge': None
            },
            {
                'name': 'Create Quotation',
                'description': 'Generate new quotations for customers',
                'link': reverse('create_quotation_page'),
                'icon': 'notika-icon notika-file',
                'category': 'Dashboard',
                'keywords': ['quotation', 'quote', 'estimate', 'proposal'],
                'badge': None
            },
            
            # STOCK MANAGEMENT
            {
                'name': 'Products',
                'description': 'Manage product catalog',
                'link': reverse('products_page'),
                'icon': 'notika-icon notika-box',
                'category': 'Stock',
                'keywords': ['products', 'items', 'goods', 'catalog', 'inventory'],
                'badge': None
            },
            {
                'name': 'Stock',
                'description': 'View and manage current stock levels',
                'link': reverse('stocks_page'),
                'icon': 'notika-icon notika-warehouse',
                'category': 'Stock',
                'keywords': ['stock', 'inventory', 'quantity', 'levels', 'available'],
                'badge': None
            },
            {
                'name': 'Batches',
                'description': 'Manage product batches and lots',
                'link': reverse('batches_page'),
                'icon': 'notika-icon notika-layers',
                'category': 'Stock',
                'keywords': ['batches', 'lots', 'batch numbers', 'expiry'],
                'badge': None
            },
            {
                'name': 'Stock Adjustments',
                'description': 'Adjust stock quantities',
                'link': reverse('batch_adjustments_page'),
                'icon': 'notika-icon notika-edit',
                'category': 'Stock',
                'keywords': ['stock adjustments', 'adjust', 'modify stock', 'quantity change'],
                'badge': None
            },
            {
                'name': 'Mass Price Adjustment',
                'description': 'Bulk update product prices',
                'link': reverse('mass_price_adjustments_page'),
                'icon': 'notika-icon notika-dollar',
                'category': 'Stock',
                'keywords': ['mass price', 'bulk price', 'price update', 'price adjustment'],
                'badge': None
            },
            {
                'name': 'Categories',
                'description': 'Organize products into categories',
                'link': reverse('categories_page'),
                'icon': 'notika-icon notika-folder',
                'category': 'Stock',
                'keywords': ['categories', 'product types', 'classification'],
                'badge': None
            },
            
            # SALES & TRANSACTIONS
            {
                'name': 'Sales',
                'description': 'View and manage sales records',
                'link': reverse('sales_page'),
                'icon': 'notika-icon notika-dollar',
                'category': 'Sales',
                'keywords': ['sales', 'revenue', 'income', 'transactions'],
                'badge': None
            },
            {
                'name': 'Receiving Invoices',
                'description': 'Manage incoming invoices',
                'link': reverse('invoices_page'),
                'icon': 'notika-icon notika-invoice',
                'category': 'Sales',
                'keywords': ['receiving invoices', 'incoming invoices', 'purchase invoices'],
                'badge': None
            },
            {
                'name': 'Credit Notes',
                'description': 'Manage credit notes and adjustments',
                'link': reverse('credit_notes_page'),
                'icon': 'notika-icon notika-credit',
                'category': 'Sales',
                'keywords': ['credit notes', 'credit', 'adjustments', 'refund', 'returns'],
                'badge': None
            },
            {
                'name': 'Transactions',
                'description': 'View all financial transactions',
                'link': reverse('sales_transactions_page'),
                'icon': 'notika-icon notika-credit-card',
                'category': 'Sales',
                'keywords': ['transactions', 'payments', 'financial', 'records'],
                'badge': None
            },
            {
                'name': 'Returns Out',
                'description': 'Manage outgoing returns to suppliers',
                'link': reverse('returns_out_page'),
                'icon': 'notika-icon notika-return',
                'category': 'Sales',
                'keywords': ['returns out', 'supplier returns', 'send back'],
                'badge': None
            },
            
            # EXPENSES
            {
                'name': 'Expenses',
                'description': 'Track and manage business expenses',
                'link': reverse('expenses_page'),
                'icon': 'notika-icon notika-wallet',
                'category': 'Expenses',
                'keywords': ['expenses', 'costs', 'spending', 'outgoing'],
                'badge': None
            },
            {
                'name': 'Expense Types',
                'description': 'Configure expense categories',
                'link': reverse('expense_types_page'),
                'icon': 'notika-icon notika-tag',
                'category': 'Expenses',
                'keywords': ['expense types', 'cost categories', 'spending types'],
                'badge': None
            },
            
            # UTILITIES
            {
                'name': 'Departments',
                'description': 'Organize users by department',
                'link': reverse('departments_page'),
                'icon': 'notika-icon notika-building',
                'category': 'Utilities',
                'keywords': ['departments', 'teams', 'divisions', 'groups'],
                'badge': None
            },
            {
                'name': 'Batch Adjustment Reasons',
                'description': 'Configure reasons for batch adjustments',
                'link': reverse('batch_adjustment_reasons_page'),
                'icon': 'notika-icon notika-list',
                'category': 'Utilities',
                'keywords': ['adjustment reasons', 'stock reasons', 'batch reasons'],
                'badge': None
            },
            {
                'name': 'Stock Return Reasons',
                'description': 'Configure reasons for stock returns',
                'link': reverse('return_reasons_page'),
                'icon': 'notika-icon notika-question',
                'category': 'Utilities',
                'keywords': ['return reasons', 'stock return', 'return causes'],
                'badge': None
            },
            {
                'name': 'Currencies',
                'description': 'Configure payment options',
                'link': reverse('payment_methods_page'),
                'icon': 'notika-icon notika-payment',
                'category': 'Utilities',
                'keywords': ['payment methods', 'payment types', 'currencies', 'rate'],
                'badge': None
            },
            {
                'name': 'VAT Codes',
                'description': 'Manage VAT rates and codes',
                'link': reverse('VATcodes_page'),
                'icon': 'notika-icon notika-percentage',
                'category': 'Utilities',
                'keywords': ['vat', 'tax', 'tax rates', 'gst', 'hst'],
                'badge': None
            },
            
            # SETTINGS & CONFIGURATION
            {
                'name': 'Settings',
                'description': 'Global system settings and preferences',
                'link': reverse('system_settings'),
                'icon': 'notika-icon notika-settings',
                'category': 'Settings',
                'keywords': ['settings', 'config', 'preferences', 'system'],
                'badge': None
            },
            {
                'name': 'Store Configurations',
                'description': 'Store-specific settings and preferences',
                'link': reverse('client_settings_page'),
                'icon': 'notika-icon notika-config',
                'category': 'Settings',
                'keywords': ['store config', 'store settings', 'store profile', 'client config'],
                'badge': None
            },
            {
                'name': 'Fiscalisation',
                'description': 'Fiscal compliance and reporting',
                'link': reverse('fiscalisation:dashboard'),
                'icon': 'notika-icon notika-document',
                'category': 'Settings',
                'keywords': ['fiscalisation', 'fiscal', 'compliance', 'tax reporting'],
                'badge': None
            },
            
            # ACCOUNTS & PEOPLE
            {
                'name': 'Customers',
                'description': 'Manage customer accounts',
                'link': reverse('customers_page'),
                'icon': 'notika-icon notika-person',
                'category': 'Accounts',
                'keywords': ['customers', 'clients', 'buyers', 'accounts'],
                'badge': None
            },
            {
                'name': 'Suppliers',
                'description': 'Manage supplier/vendor accounts',
                'link': reverse('suppliers_page'),
                'icon': 'notika-icon notika-truck',
                'category': 'Accounts',
                'keywords': ['suppliers', 'vendors', 'providers', 'sourcing'],
                'badge': None
            },
            {
                'name': 'Manufacturers',
                'description': 'Manage product manufacturers',
                'link': reverse('manufacturers_page'),
                'icon': 'notika-icon notika-factory',
                'category': 'Accounts',
                'keywords': ['manufacturers', 'brands', 'producers', 'makers'],
                'badge': None
            },
            {
                'name': 'Users',
                'description': 'Manage system users and permissions',
                'link': reverse('users_page'),
                'icon': 'notika-icon notika-users',
                'category': 'Accounts',
                'keywords': ['users', 'staff', 'employees', 'permissions'],
                'badge': None
            },
            
            # DATA ANALYSIS & REPORTS
            {
                'name': 'Transactions Summary',
                'description': 'Overview of all transactions',
                'link': reverse('transactions_summery_page'),
                'icon': 'notika-icon notika-chart-bar',
                'category': 'Analysis',
                'keywords': ['transactions summary', 'summary', 'overview', 'total'],
                'badge': None
            },
            {
                'name': 'Stock Analysis',
                'description': 'Analyze stock performance and trends',
                'link': reverse('stock_analysis_page'),
                'icon': 'notika-icon notika-chart-line',
                'category': 'Analysis',
                'keywords': ['stock analysis', 'inventory analysis', 'trends', 'performance'],
                'badge': None
            },
            {
                'name': 'Comparative Stock Analysis',
                'description': 'Compare stock across periods or categories',
                'link': reverse('comparative_stock_analysis_page'),
                'icon': 'notika-icon notika-compare',
                'category': 'Analysis',
                'keywords': ['comparative', 'compare stock', 'comparison', 'period comparison'],
                'badge': None
            },
            {
                'name': 'Periodic Reports',
                'description': 'Generate reports for specific time periods',
                'link': reverse('periodic_reports_page'),
                'icon': 'notika-icon notika-calendar',
                'category': 'Analysis',
                'keywords': ['periodic reports', 'time period', 'reports', 'date range'],
                'badge': None
            },
            {
                'name': 'Specified Reports',
                'description': 'Custom and filtered reports',
                'link': reverse('specified_reports_page'),
                'icon': 'notika-icon notika-file-report',
                'category': 'Analysis',
                'keywords': ['specified reports', 'custom reports', 'filtered reports'],
                'badge': None
            },
            
            # DATA & STORAGE
            {
                'name': 'Backup',
                'description': 'System backup and restore',
                'link': reverse('create_backup'),
                'icon': 'notika-icon notika-cloud',
                'category': 'Storage',
                'keywords': ['backup', 'restore', 'data', 'archive'],
                'badge': None
            },
            
            # SECURITY
            {
                'name': 'Logout',
                'description': 'Sign out of the system',
                'link': reverse('user_logout'),
                'icon': 'notika-icon notika-logout',
                'category': 'Security',
                'keywords': ['logout', 'sign out', 'exit', 'log off'],
                'badge': None
            }
        ]
        # If you have dynamic features from database, add them here
        # Example: features.extend(get_dynamic_features_from_db())
        
        return JsonResponse({
            'features': features,
            'total': len(features),
            'status': 'success'
        })
        
    except Exception as e:
        print(f"Error loading search features: {str(e)}")
        return JsonResponse({
            'features': [],
            'total': 0,
            'status': 'error',
            'message': str(e)
        }, status=500)





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
            order_profile = SubscriptionManager.objects.all().first()
            
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