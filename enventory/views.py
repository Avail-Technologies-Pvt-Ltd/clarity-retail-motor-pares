import os
import time
import threading

from django.shortcuts import render


# models
from .models import *
from payments.models import *
from accounts.models import ClientSetting
from knowledge_base.models import Compatibility
from pos.models import CartItem, QuotationItem


from print_out.print_client import print_this_document, get_printer, get_fiscal_details

import json

from django.contrib import messages as message

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse

from reports.views import activate_all_deactivated_batches


from payments.models import Sale
# ------------------------------------------------------------------------



from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from django.db.models.functions import Concat
from django.db.models import Q, CharField, Value as V

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from reusable_functions.univesal.decorators import role_validator
from reusable_functions.univesal.client_spacific_functions.client_spacific_functions import  print_formated_text
from reusable_functions.univesal.notifications import  delete_notifications_by_type
from reusable_functions.univesal.client_spacific_functions.client_spacific_functions import print_credit_note, print_out_credit_note_bulk
from reusable_functions.univesal.custom_log import log_activity
from reusable_functions.univesal.fiscalisation import is_correct_hs_code_format


from django.contrib.auth.decorators import login_required
from django.db import transaction



import locale
locale.setlocale(locale.LC_ALL, '') 


try:
    configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
    pagination_slice_leangth = configuration.pagination_slice_leangth
except Exception as e:
    HttpResponseRedirect('client_settings_page')


# ------------------------------------------------------------------------
# HTML PAGES
# ------------------------------------------------------------------------

@login_required
def departments_page(request):
    return render(request, 'enventory/departments_page.html')

@login_required
def categories_page(request):
    return render(request, 'enventory/categories_page.html')

@login_required
def notifications_page(request):
    return render(request, 'enventory/notifications_page.html')

@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def returns_out_page(request):
    return render(request, 'enventory/returns_out_page.html')

@login_required
def lables_page(request):
    return render(request, 'enventory/lables_page.html')

@login_required
def return_reasons_page(request):
    return render(request, 'enventory/return_reasons_page.html')

@login_required
def invoices_page(request):
    return render(request, 'enventory/invoices_page.html')

@login_required
def credit_notes_page(request):
    return render(request, 'enventory/credit_notes_page.html')

@login_required
def products_page(request):
    return render(request, 'enventory/products_page.html')

@login_required
def stocks_page(request):
    return render(request, 'enventory/stocks_page.html')

@login_required
def notifications_page(request):
    return render(request, 'enventory/notifications_page.html')

@login_required
def batches_page(request):
    return render(request, 'enventory/batches_page.html')

@login_required
def batch_adjustments_page(request):
    return render(request, 'enventory/batch_adjustments_page.html')

@login_required
def batch_adjustment_reasons_page(request):
    return render(request, 'enventory/batch_adjustment_reasons_page.html')

@login_required
def mass_price_adjustments_page(request):
    return render(request, 'enventory/mass_price_adjustments_page.html')



# ------------------------------------------------------------------------
# //HTML PAGES
# ------------------------------------------------------------------------

# ------------------------------------------------------------------------
# //AJAX
# ------------------------------------------------------------------------


from django.db.models import Sum


def print_out_stock_summary_to_pos(request):
    OLD_PRINT = os.getenv("OLD_PRINT", "false").lower() == "true"
    
    if OLD_PRINT:
        return print_out_stock_summary_to_pos_new(request)

    else:
        return print_out_stock_summary_to_pos_new(request)



def print_out_stock_summary_to_pos_new(request):
    from print_out.print_client import test_printer, print_this_document

    printer = get_printer(request)
    print_this_document(request, printer, "STOCKSUMMARY", 0, "")

    return JsonResponse({'custome_status': '', 'message': str("Print job sent")})




def get_stock_value_summary(request):
    try:
        today = datetime.now().date()
        
        # Active batches: not deleted, status True, not expired
        active_batches = Batch.objects.filter(
            deleted=False,
            status=True,
            expiration_date__gt=today
        )
        
        # Calculate total purchase value using buying_unit_price * total_units
        total_purchase = Decimal('0.00')
        for batch in active_batches:
            if batch.buying_unit_price and batch.total_units:
                # buying_unit_price is the cost per unit
                total_purchase += batch.buying_unit_price * batch.total_units
        
        # Calculate total units
        total_units = active_batches.aggregate(
            total=Sum('total_units')
        )['total'] or 0
        
        # Calculate selling value from stock (available units × selling price)
        total_selling = Decimal('0.00')
        stocks_with_batches = Stock.objects.filter(
            deleted=False,
            status=True,
            batch__in=active_batches
        ).distinct()
        
        for stock in stocks_with_batches:
            stock_units = Batch.objects.filter(
                stock=stock,
                deleted=False,
                status=True,
                expiration_date__gt=today
            ).aggregate(total=Sum('total_units'))['total'] or 0
            
            # Selling value = available units × selling price per unit
            total_selling += stock.selling_price * stock_units
        
        total_profit = total_selling - total_purchase
        
        return JsonResponse({
            'custome_status': 'Success',
            'total_purchase_value': float(total_purchase),
            'total_selling_value': float(total_selling),
            'total_profit_potential': float(total_profit),
            'profit_margin_percentage': float(
                (total_profit / total_selling * 100) 
                if total_selling > 0 else 0
            ),
            'total_units': total_units,
            'total_products': stocks_with_batches.count(),
            'generated_at': datetime.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'custome_status': 'Error', 
            'message': str(e)
        })




@login_required
@role_validator(['Supervisor'])
@transaction.atomic
def delete_category(request):
    try:
        category_id = request.GET.get('category_id')
        
        if not category_id:
            return JsonResponse({'type': "error", 'title': "Error", 'message': "Category ID required"}, status=400)
        
        category = Category.objects.get(id=int(category_id))
        products = Product.objects.filter(category=category)
        
        # Check for dependencies
        if products.exists():
            return JsonResponse({
                'type': "warning",
                'title': "Cannot Delete",
                'message': f"This category has {products.count()} product(s) associated. Please remove all products first before deleting this category."
            })
        
        # Delete category
        category.delete()
        
        return JsonResponse({
            'type': "success",
            'title': "Deleted!", 
            'message': "Category deleted successfully!"
        })
        
    except Category.DoesNotExist:
        return JsonResponse({'type': "error", 'title': "Error", 'message': f"Category not found"}, status=404)
    except Exception as e:
        return JsonResponse({'type': "error", 'title': "Error", 'message': str(e)}, status=500)



@login_required
@role_validator(['Supervisor'])
@transaction.atomic
def delete_department(request):
    try:
        department_id = request.GET.get('department_id')
        
        if not department_id:
            return JsonResponse({'type': "error", 'title': "Error", 'message': "Department ID required"}, status=400)
        
        department = Department.objects.get(id=int(department_id))
        products = Product.objects.filter(department=department)
        
        # Check for dependencies
        if products.exists():
            return JsonResponse({
                'type': "warning",
                'title': "Cannot Delete",
                'message': f"This department has {products.count()} product(s) associated. Please remove all products first before deleting this department."
            })
        
        # Delete department
        department.delete()
        
        return JsonResponse({
            'type': "success",
            'title': "Deleted!", 
            'message': "Department deleted successfully!"
        })
        
    except Department.DoesNotExist:
        return JsonResponse({'type': "error", 'title': "Error", 'message': f"Department not found"}, status=404)
    except Exception as e:
        return JsonResponse({'type': "error", 'title': "Error", 'message': str(e)}, status=500)



@login_required
@role_validator(['Data Analyst','Supervisor'])
def ajax_departments_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        departments = Department.objects.filter(deleted=False).order_by('title')


    if request_type == "FORM-FILTER":
        # form filterr here
        departments = Department.objects.filter(deleted=False).order_by('title')

    
    #------------------------------------------------------------------------------ 
    data_queryset = departments
    paginator = Paginator(data_queryset, pagination_slice_leangth)  # Load 20 items per page
    # print(paginator)
    page = request.GET.get('page')
    # page = 1
    # print(page)

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
                <th>Department</th>
                <th>Created by</th>
                <th>Date Created</th>
                <th>Total Products</th>
                <th colspan="2">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for department in data_page:
        row = f"""
            <tr>
                <td>
                    { department.title }<br>
                    <small>{ department.description }</small>
                </td>
                <td>{ department.created_by } </td>
                <td>{ str(department.created_at)[:10] }</td>
                <td>{ locale.format_string('%.0f', department.total_products, grouping=True) } </td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ department.id }" type="button"  data-toggle="modal" data-target="#updateDepartmentModal" id="update-department-modal-button"><i class="notika-icon notika-edit"></a></td>
                <td>
                    <a href="#" class="btn btn-primary" onclick="deleteDepartment({ department.id })">
                        <i class="notika-icon notika-trash"></i>
                    </a>
                </td>
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
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer


    table_summery = f" {departments.count()} out of {Department.objects.all().count()} batch adjustment reasons."
    # print(f"DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD: {str(data_page)}")
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})


@login_required
@role_validator(['Data Analyst','Supervisor'])
def ajax_categories_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        categories = Category.objects.filter(deleted=False).order_by('title')


    if request_type == "FORM-FILTER":
        # form filterr here
        categories = Category.objects.filter(deleted=False).order_by('title')

    
    #------------------------------------------------------------------------------ 
    data_queryset = categories
    paginator = Paginator(data_queryset, pagination_slice_leangth)  # Load 20 items per page
    # print(paginator)
    page = request.GET.get('page')
    # page = 1
    # print(page)

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
                <th>Created by</th>
                <th>Date Created</th>
                <th>Total Products</th>
                <th colspan="2">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for category in data_page:
        row = f"""
            <tr>
                <td>
                    { category.title }<br>
                    <small>{ category.description }</small>
                </td>
                <td>{ category.created_by } </td>
                <td>{ str(category.created_at)[:10] }</td>
                <td>{ locale.format_string('%.0f', category.total_products, grouping=True) } </td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ category.id }" type="button"  data-toggle="modal" data-target="#updateCategoryModal" id="update-category-modal-button"><i class="notika-icon notika-edit"></a></td>
                <td>
                    <a href="#" class="btn btn-primary" onclick="deleteCategory({ category.id })">
                        <i class="notika-icon notika-trash"></i>
                    </a>
                </td>
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
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer


    table_summery = f" {categories.count()} out of {Category.objects.all().count()} batch adjustment reasons."
    # print(f"DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD: {str(data_page)}")
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})



@login_required
@role_validator(['Supervisor'])
def add_department(request):
    title = request.GET.get('title')
    description = request.GET.get('description')

    already_exist = Department.objects.filter(title__iexact=title)
    if already_exist:
        return JsonResponse({"custome_status":"Error", "message":"A department with the same title already exist!"})
    else:
        try:
            new_department = Department()
            new_department.title = title
            new_department.description = description
            new_department.created_by = request.user
            new_department.save()
            return JsonResponse({"custome_status":"", "message":"New department added succesefully!"})

        except Exception as e:
            return JsonResponse({"custome_status":"Error", "message": str(e)})



@login_required
@role_validator(['Supervisor'])
def add_category(request):
    title = request.GET.get('title')
    description = request.GET.get('description')

    already_exist = Category.objects.filter(title__iexact=title)
    if already_exist:
        return JsonResponse({"custome_status":"Error", "message":"An category with the same title already exist!"})
    else:
        try:
            new_category = Category()
            new_category.title = title
            new_category.description = description
            new_category.created_by = request.user
            new_category.save()
            return JsonResponse({"custome_status":"", "message":"New category added succesefully!"})

        except Exception as e:
            return JsonResponse({"custome_status":"Error", "message": str(e)})



@login_required
@role_validator(['Supervisor'])
def update_department(request):
    department_id = request.GET.get('department_id')
    title = request.GET.get('title')
    description = request.GET.get('description')
   

    department = Department.objects.get(id=int(department_id))
    already_exist = Department.objects.filter(title=title, description=description).exclude(id=int(department_id))
    if already_exist:
        return JsonResponse({"custome_status":"Error", "message":"A department with the same title and detals alread exist!"})
    try:
        department.title = title
        department.description = description
        department.created_by = request.user
        department.save()

        return JsonResponse({"custome_status":"", "message":"Department updated succesefully!"})
    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})



@login_required
@role_validator(['Supervisor'])
def update_category(request):
    category_id = request.GET.get('category_id')
    title = request.GET.get('title')
    description = request.GET.get('description')
   

    category = Category.objects.get(id=int(category_id))
    already_exist = Category.objects.filter(title=title, description=description).exclude(id=int(category_id))
    if already_exist:
        return JsonResponse({"custome_status":"Error", "message":"A category with the same title and detals alread exist!"})
    try:
        category.title = title
        category.description = description
        category.created_by = request.user
        category.save()

        return JsonResponse({"custome_status":"", "message":"Category updated succesefully!"})
    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def get_department_details(request):
    department_id = request.GET.get('department_id')
    department = Department.objects.get(id=int(department_id))

    title = department.title
    description = department.description
    created_by = f"{ department.created_by.first_name.title() } { department.created_by.last_name.title() }" if department.created_by else ""
    created_at = str(department.created_at)[:10]
 

    details = {
        "title": title,
        "description": description,
        "created_by": created_by,
        "created_at": created_at,
    }
    return JsonResponse({"details":details, "message":"New department served succesefully!"})



@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def get_category_details(request):
    category_id = request.GET.get('category_id')
    category = Category.objects.get(id=int(category_id))

    title = category.title
    description = category.description
    created_by = f"{ category.created_by.first_name.title() } { category.created_by.last_name.title() }" if category.created_by else ""
    created_at = str(category.created_at)[:10]
 

    details = {
        "title": title,
        "description": description,
        "created_by": created_by,
        "created_at": created_at,
    }
    return JsonResponse({"details":details, "message":"New category served succesefully!"})


@login_required
@role_validator(['Supervisor'])
@transaction.atomic
def update_visible_stock_prices(request):
    try:
        """
        Handle visible page stock price updates
        Receives: {"updated_prices": [{"stock_id": 1, "new_price": 150.00}, ...]}
        """
        try:
            updated_prices_json = request.POST.get('updated_prices')
            if not updated_prices_json:
                return JsonResponse({
                    'success': False,
                    'message': 'No data received'
                }, status=400)
            
            updated_prices = json.loads(updated_prices_json)
            
            if not isinstance(updated_prices, list):
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid data format'
                }, status=400)
            
            updated_count = 0
            errors = []
            
            for item in updated_prices:
                stock_id = item.get('stock_id')
                new_price = item.get('new_price')
                
                if not stock_id or new_price is None:
                    errors.append(f'Missing data for item: {item}')
                    continue
                
                try:
                    stock = Stock.objects.get(id=stock_id)
                    stock.selling_price = float(new_price)
                    stock.save()
                    updated_count += 1
                except Stock.DoesNotExist:
                    errors.append(f'Stock with id {stock_id} not found')
                except Exception as e:
                    errors.append(f'Error updating stock {stock_id}: {str(e)}')
            
            if errors:
                return JsonResponse({
                    'success': True if updated_count > 0 else False,
                    'message': f'Updated {updated_count} items. Errors: {", ".join(errors)}',
                    'updated_count': updated_count,
                    'errors': errors
                })
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully updated {updated_count} stock items',
                'updated_count': updated_count
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)



@login_required
@role_validator(['Supervisor'])
def update_all_stock_prices(request):
    """
    Handle all stock price updates with formula
    Receives: {
        "price_direction": "increase|decrease|neutral",
        "price_value": 10.5,
        "price_type": "percentage|fixed",
        "price_base": "selling|buying"
    }
    """
    try:
        price_direction = request.POST.get('price_direction')
        price_value = request.POST.get('price_value')
        price_type = request.POST.get('price_type')
        price_base = request.POST.get('price_base')
        
        # Validate required fields
        if not all([price_direction, price_value, price_type, price_base]):
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields'
            }, status=400)
        
        # Convert price_value to float
        try:
            price_value = float(price_value)
        except (TypeError, ValueError):
            return JsonResponse({
                'success': False,
                'message': 'Invalid price value'
            }, status=400)
        
        # Get all stock items
        stocks = Stock.objects.all()
        updated_count = 0
        errors = []
        
        for stock in stocks:
            try:
                # Get base price
                if price_base == 'selling':
                    base_price = stock.selling_price
                else:  # buying
                    base_price = stock.avarage_unit_cost
                
                # Calculate adjustment
                if price_type == 'percentage':
                    adjustment = (price_value / 100) * base_price
                else:  # fixed
                    adjustment = price_value
                
                # Apply adjustment
                if price_direction == 'increase':
                    new_price = stock.selling_price + adjustment
                elif price_direction == 'decrease':
                    new_price = stock.selling_price - adjustment
                else:  # neutral
                    new_price = price_value
                
                # Ensure price is not negative
                new_price = max(0, new_price)
                
                # Save updated price
                stock.selling_price = new_price
                stock.save()
                updated_count += 1
                
            except Exception as e:
                errors.append(f'Error updating stock {stock.id}: {str(e)}')
        
        if errors:
            return JsonResponse({
                'success': True if updated_count > 0 else False,
                'message': f'Updated {updated_count} items. Errors: {", ".join(errors)}',
                'updated_count': updated_count,
                'errors': errors
            })
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully updated {updated_count} stock items',
            'updated_count': updated_count,
            'data': {
                'direction': price_direction,
                'value': price_value,
                'type': price_type,
                'base': price_base
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


#   edit
def on_pos_change_price(request):
    stock_id = request.GET.get('stock_id')
    new_price = float(request.GET.get('new_price'))
    stock = Stock.objects.get(id=int(stock_id))
    original_price = stock.selling_price

    if new_price >= original_price:
        stock.selling_price = new_price
        stock.created_by = request.user
        stock.save()
        return JsonResponse({"custome_status":"", "message":"Stock price updated succesefully!"})
    else:
        if "Supervisor" in request.user.roles:
            stock.selling_price = new_price
            stock.created_by = request.user
            stock.save()
            return JsonResponse({"custome_status":"", "message":"Stock price updated succesefully!"})
        else:
            return JsonResponse({"custome_status":"Error", "message":"You are not authorised to lower the price, you can only rise."})



@login_required
@role_validator(['Supervisor'])
def update_product(request):
    title = request.GET.get('title')
    hs_code = request.GET.get('hs_code')
    details = request.GET.get('details')
    product_code = request.GET.get('product_code')
    status = request.GET.get('status')
    product_id = request.GET.get('product_id')
    category = request.GET.get('category')
    department = request.GET.get('department')
    vat_code = request.GET.get('vat_code')

    product = Product.objects.get(id=int(product_id))
    already_exist = Product.objects.filter(title=title, details=details).exclude(id=int(product_id))
    if already_exist:
        return JsonResponse({"custome_status":"Error", "message":"A product with the same title and detals alread exist!"})
    try:
        product.title = title
        product.details = details
        product.zimra_hs_code = hs_code
        product.product_code = product_code
        product.vat_code = VATCode.objects.get(id=int(vat_code))
        try:
            product.category = Category.objects.get(id=int(category))
        except:
            pass

        try:
            product.department = Department.objects.get(id=int(department))
        except:
            pass
        product.status = status

        if hs_code != "" and is_correct_hs_code_format(hs_code) == False:
            return JsonResponse({"custome_status":"Error", "message":"You have entered an Invalid HS Code formart. If you leave it blank and it will use the VAT Code default"})

        product.save()

        return JsonResponse({"custome_status":"", "message":"Product updated succesefully!"})
    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":str(e)})






@login_required
@role_validator(['Supervisor'])
def update_temporary_invoice_item(request):
    temporary_invoice_item_id = request.GET.get('temporary_invoice_item_id')
    stock = request.GET.get('stock_')
    stock = Stock.objects.get(id=int(stock))

    manufacturer = request.GET.get('manufacturer')
    manufacturer = Manufacturer.objects.get(id=int(manufacturer))

    selling_price_type = request.GET.get('selling_price_type')
    selling_price_number = float(request.GET.get('selling_price_number'))
    total_packs = int(request.GET.get('total_packs'))
    pack_size = int(request.GET.get('pack_size'))
    buying_pack_price = float(request.GET.get('buying_pack_price'))
    expiration_date = request.GET.get('expiration_date')
    discount_type = request.GET.get('discount_type')
    discount_number = float(request.GET.get('discount_number'))
    batch_number = request.GET.get('batch_number')
   

    #try collect and culculete
    try:
        temporary_invoice = TemporaryInvoice.objects.filter(created_by=request.user)[0]
    except:
        message = 'You need to create an invoice first in "Invoice" tab.' 
        return JsonResponse({"custome_status":"Error","message":message})
        
    vat_price = (float(stock.product.vat_code.percentage) * 0.01) * (total_packs * buying_pack_price)
    vat_percentage = float(stock.product.vat_code.percentage) * 0.01

    if discount_type == "DISCOUNT PERCENTAGE":
        discount_price = (total_packs * buying_pack_price) * (discount_number * 0.01)
        discount_percentage = discount_number

    elif discount_type == "DISCOUNT PRICE":
        discount_price = discount_number
        discount_percentage = (discount_number * 0.01) * (total_packs * buying_pack_price)
    else:
        message = "You can not use the selected discount type."
        return JsonResponse({'message': message})


    total_buying_pack_price = buying_pack_price #- discount_price

    if selling_price_type == "MARKUP PERCENTAGE":
        markup = selling_price_number
        selling_price = (markup / 100) * buying_unit_cost + buying_unit_cost 
    elif selling_price_type == "SELLING PRICE":
        selling_price = selling_price_number
        buying_unit_cost = buying_pack_price / pack_size
        markup = (selling_price - buying_unit_cost)/(buying_unit_cost)*100

    # if selling_price_type == "MARKUP PERCENTAGE":
    #     markup = (selling_price_number/100) * (total_buying_pack_price/pack_size) 
    #     selling_price = (total_buying_pack_price / pack_size) + markup
    # elif selling_price_type == "SELLING PRICE":
    #     markup = selling_price_number - (total_buying_pack_price/pack_size) 
    #     selling_price = selling_price_number
    elif selling_price_type == "EXISTING PRICE":
        try:
            markup = stock.markup
            selling_price = stock.selling_price
        except Exeption as e:
            return JsonResponse({'custome_status':'Error', 'message': "Error! You do not have an existing price  for this stock yet"})
    else:
        message = "You can not use the selected markup type."
        return JsonResponse({'message': message})



    # try  save:
    temporary_invoice_item = TemporaryInvoiceItem.objects.get(id=int(temporary_invoice_item_id))
    temporary_invoice_item.invoice = temporary_invoice
    temporary_invoice_item.stock = stock
    temporary_invoice_item.selling_price_type = selling_price_type
    temporary_invoice_item.selling_price_number = selling_price_number
    temporary_invoice_item.discount_type = discount_type
    temporary_invoice_item.discount_number = discount_number
    temporary_invoice_item.manufacturer = manufacturer
    temporary_invoice_item.vat_price = vat_price
    temporary_invoice_item.vat_percentage = vat_percentage
    temporary_invoice_item.discount_price = discount_price
    temporary_invoice_item.discount_percentage = discount_percentage
    temporary_invoice_item.total_packs = total_packs
    temporary_invoice_item.pack_size = pack_size
    temporary_invoice_item.buying_pack_price = buying_pack_price
    temporary_invoice_item.total_buying_pack_price = total_buying_pack_price
    temporary_invoice_item.markup = markup
    temporary_invoice_item.selling_price = selling_price
    temporary_invoice_item.expiration_date = expiration_date
    temporary_invoice_item.batch_number = batch_number

    temporary_invoice_item.save()

    print('temporary_invoice_item.markup')
    print(temporary_invoice_item.markup)

    return JsonResponse({"custome_status":"", "message":"Invoice item updated succesefully!"})





@login_required
@role_validator(['Supervisor'])
def activate_deactivate_batch(request):
    batch_id = request.GET.get('batch_id')
    batch = Batch.objects.get(id=int(batch_id))
    status = request.GET.get('status')
    if status == "True":
        status = True
    else:
        status = False

    batch.status = status
    batch.save()
    if batch.status == True:
        return JsonResponse({"custome_status":"", "message":"Batch activated succesefully!"})
    else:
        return JsonResponse({"custome_status":"", "message":"Batch deactivated succesefully!"})




@login_required
@role_validator(['Supervisor'])
def save_stock_adjustments(request):
    try:
        selling_price_type = request.GET.get('selling_price_type')
        selling_price_number = float(request.GET.get('selling_price_number'))
        reorder_quantity = request.GET.get('reorder_quantity')
        expiration_warning_days = request.GET.get('expiration_warning_days')
        status = request.GET.get('status')
        stock_id = request.GET.get('stock_id')
        
        stock = Stock.objects.get(id=int(stock_id))
        if selling_price_type == "MARKUP PERCENTAGE":
            markup = float(selling_price_number/100) * float(stock.avarage_unit_cost) 
            selling_price = float(stock.avarage_unit_cost) + markup
        else:
            markup = float(selling_price_number) - float(stock.avarage_unit_cost) 
            selling_price = selling_price_number

        
        stock.selling_price = selling_price
        stock.markup = markup
        stock.reorder_quantity = int(reorder_quantity)
        stock.expiration_warning_days = expiration_warning_days
        if status == "False":
            stock.status = False
        else:
            stock.status = True
        stock.stock_id = stock_id
        stock.created_by = request.user
        stock.save()
    except Exeption as e:
        return JsonResponse({"custome_status":"Error", "message":e})
    return JsonResponse({"custome_status":"", "message":"Stock adjusted succesefully!"})




#   details

@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def print_all_stock_for_reconcile(request):
    stock_list = Stock.objects.filter(status=True).order_by('-product__category__title')
    counter = 0
    stock_list_print_out = f"""----------------------------------------------
----------------------------------------------
                    STOCK LIST

AS OF: {str(datetime.today())[:16]}
PRINTED BY: { request.user.first_name.title() } { request.user.first_name.title() }
----------------------------------------------
PRODUCT                               IN STOCK
----------------------------------------------
    """
    for stock in stock_list:
        counter += 1
        description = f"{str(counter):>4} [{ stock.product.product_code }] { stock.product.title }"
        total_units = stock.total_units
        product_line = f"""\n{str(description)[:38]:<40} {locale.format_string('%.0f', total_units, grouping=True):>5}"""

        stock_list_print_out += product_line
    stock_list_print_out += """
----------------------------------------------
NOTE: Only active stock is printed.
    \n\n\n"""
    
    print(stock_list_print_out)
    custome_status, message = print_formated_text(stock_list_print_out)
    return JsonResponse({"type": 'success', 'title':"Done", "message": message,})

    # except Exception as e:
    #     return JsonResponse({"type": 'error', 'title':"Error!", "message": f"{e}"})


def print_out_order_list(request):
    OLD_PRINT = os.getenv("OLD_PRINT", "false").lower() == "true"
    
    if OLD_PRINT:
        return print_out_order_list_old(request)

    else:
        return print_out_order_list_new(request)



@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def print_out_order_list_new(request):
    try:
        from reports.views import tester
        from print_out.print_client import print_this_document

        from print_out.print_client import test_printer, print_this_document
    
        # Get printer from database
        printer = get_printer(request)
        print_this_document(request, printer, "ORDERLIST", 0, "")

    except Exception as e:
        return JsonResponse({"custome_status": "Error", "message": f"{e}"})


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def print_out_order_list_old(request):
    try:
        order_list_array = request.GET.getlist('order_list_array')
        order_list_array = str(order_list_array)[2:-2]

        # Parse the JSON string into a Python list of dictionaries
        data = json.loads(order_list_array)

        # Iterate over the list of dictionaries and print the values
        order_list_print_out = f"""----------------------------------------------
DATE: {datetime.strptime(str(datetime.today())[:10],"%Y-%m-%d").date()}
PREPARED BY: { request.user.first_name.title() } { request.user.first_name.title() }
----------------------------------------------
PRODUCT                           [STOCK]  BUY
----------------------------------------------
        """
        for item in data:
            product_line = f"""\n{str(item['productDescription'])[:34]:<34} [{item['totalUnitsAvailable']:>3}] {item['orderQuantity']:>5}"""

            order_list_print_out += product_line
        order_list_print_out += """
----------------------------------------------

                *STAMP*
        \n\n\n"""
        
        print(order_list_print_out)
        custome_status, message = print_formated_text(order_list_print_out)
        return JsonResponse({"custome_status": custome_status, "message": message,})

    except Exception as e:
        return JsonResponse({"custome_status": "Error", "message": f"{e}"})



@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def get_reorder_suggestion_list(request):
    running_out_stock = Stock.objects.filter(status=True, deleted=False)#, reorder_flag=True)

    table = ""
    for item in running_out_stock:
        if item.total_units <= item.reorder_quantity:
            table += f"""
                <tr>
                    <td><input type="checkbox" class="select-item" data-item-id="{ item.id }"></td>
                    <td id="product-description" >({ item.product.product_code }) { item.product.title }</td>
                    <td id="avarege-unit-cost" style="text-align: right">{ locale.format_string('%.2f', item.avarage_unit_cost, grouping=True) }</td>
                    <td id="total-units-available" style="text-align: right">{ locale.format_string('%.0f', item.total_units, grouping=True) }</td>
                    <td id="order-quantity" style="text-align: right"><input style="text-align: right" type="number" class="quantity-input" data-item-id="{ item.id }" value="{ locale.format_string('%.0f',(item.reorder_quantity - item.total_units + 1) * 2, grouping=True) }"></td>
                </tr>
                """

    return JsonResponse({"custome_status": "", "table": table})



@login_required
@role_validator(['Data Analyst','Supervisor'])
@transaction.atomic
def merge_products(request):
    source_product_id = request.POST.get('source_product_id')
    destiny_product_id = request.POST.get('destiny_product_id')
    title = request.POST.get('title')
    product_code = request.POST.get('product_code')
    details = request.POST.get('details')

    # Add validation for missing products with specific error messages
    try:
        source_product = Product.objects.get(id=int(source_product_id))
    except (Product.DoesNotExist, ValueError, TypeError):
        return JsonResponse({
            'title': "Error", 
            'text': f"Source product not found", 
            'type': "error"
        })
    
    try:
        destiny_product = Product.objects.get(id=int(destiny_product_id))
    except (Product.DoesNotExist, ValueError, TypeError):
        return JsonResponse({
            'title': "Error", 
            'text': f"Destination product not found", 
            'type': "error"
        })

    existing_product = Product.objects.filter(
        Q(product_code=product_code) |
        Q(title=title, details=details)
    ).exclude(id__in=[int(destiny_product_id), int(source_product_id)])

    if existing_product.exists():
        conflict = existing_product.first()
        if conflict.title == title:
            variable = "title"
        elif conflict.product_code == product_code:
            variable = "product code"
        
        return JsonResponse({
            'title': "Error", 
            'text': f"A product with the same {variable} already exists", 
            'type': "error"
        })

    destiny_stock = Stock.objects.filter(product=destiny_product).first()

    # Properly setting all three fields
    destiny_product.title = title
    destiny_product.details = details
    destiny_product.product_code = product_code
    destiny_product.save()

    if destiny_stock:
        source_product_stock = Stock.objects.filter(product=source_product)

        for stock_to_be_deleted in source_product_stock:
            # dependances
            batchs = Batch.objects.filter(stock=stock_to_be_deleted)
            for batch in batchs:
                batch.stock = destiny_stock
                batch.save()

            invoiceitems = InvoiceItem.objects.filter(stock=stock_to_be_deleted)
            for invoiceitem in invoiceitems:
                invoiceitem.stock = destiny_stock
                invoiceitem.save()

            temporaryinvoiceitems = TemporaryInvoiceItem.objects.filter(stock=stock_to_be_deleted)
            for temporaryinvoiceitem in temporaryinvoiceitems:
                temporaryinvoiceitem.stock = destiny_stock
                temporaryinvoiceitem.save()

            returninns = ReturnInn.objects.filter(stock=stock_to_be_deleted)
            for returninn in returninns:
                returninn.stock = destiny_stock
                returninn.save()

            compatibilitys = Compatibility.objects.filter(car_part=stock_to_be_deleted)
            for compatibility in compatibilitys:
                # Check if this car_model already has compatibility with destiny stock
                if Compatibility.objects.filter(
                    car_part=destiny_stock, 
                    car_model=compatibility.car_model
                ).exists():
                    # Already exists, just delete the current one
                    compatibility.delete()
                else:
                    # Doesn't exist, transfer it
                    compatibility.car_part = destiny_stock
                    compatibility.save()

            sales = Sale.objects.filter(stock=stock_to_be_deleted)
            for sale in sales:
                sale.stock = destiny_stock
                sale.save()

            cartitems = CartItem.objects.filter(stock=stock_to_be_deleted)
            for cartitem in cartitems:
                cartitem.stock = destiny_stock
                cartitem.save()

            quotationitems = QuotationItem.objects.filter(stock=stock_to_be_deleted)
            for quotationitem in quotationitems:
                quotationitem.stock = destiny_stock
                quotationitem.save()

            stock_to_be_deleted.delete()

        source_product.delete()
    else:
        # Handle case when destiny has no stock
        # just delete source without transferring
        source_product.delete()

    return JsonResponse({'title':"Merged", 'text':"Products merged successfully", 'type':"success"})



@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def get_product_details(request):
    product_id = request.GET.get('product_id')
    product = Product.objects.get(id=int(product_id))

    title = product.title
    details = product.details
    hs_code = product.zimra_hs_code
    product_code = product.product_code
    vat_code_id = product.vat_code.id
    vat_code_text = f"{ product.vat_code.title } ({ product.vat_code.percentage })"

    category_id = product.category.id if product.category else "0"
    category_text = product.category.title if product.category else ""
    department_id = product.department.id if product.department else "0"
    department_text = product.department.title if product.department else ""

    status = product.status
    if status == True:
        status = "True"
    else:
        status = "False"

    details = {
        'title': title,
        'details': details,
        'product_code': product_code,
        'vat_code_id': vat_code_id,
        'vat_code_text': vat_code_text,
        'hs_code': hs_code,

        'category_id': category_id,
        'category_text': category_text,
        'department_id': department_id,
        'department_text': department_text,

        'status': status,
    }

    return JsonResponse({"custome_status": "", "details": details})


@login_required
@role_validator(['Data Analyst','Supervisor'])
def get_temporary_invoice_item_details(request):
    temporary_invoice_item_id = request.GET.get('temporary_invoice_item_id')
    temporary_invoice_item = TemporaryInvoiceItem.objects.get(id=int(temporary_invoice_item_id))
    stock_id = temporary_invoice_item.stock.id
    stock_text = temporary_invoice_item.stock.product.title + temporary_invoice_item.stock.product.details
    manufacturer_id = temporary_invoice_item.manufacturer.id
    manufacturer_text = temporary_invoice_item.manufacturer.company_name
    selling_price_type = temporary_invoice_item.selling_price_type
    selling_price_number = temporary_invoice_item.selling_price_number
    total_packs = temporary_invoice_item.total_packs
    pack_size = temporary_invoice_item.pack_size
    buying_pack_price = temporary_invoice_item.buying_pack_price
    expiration_date = str(temporary_invoice_item.expiration_date)[:10]
    discount_type = temporary_invoice_item.discount_type
    discount_number = temporary_invoice_item.discount_number
    batch_number = temporary_invoice_item.batch_number
    details = {
        "stock_id": stock_id,
        "stock_text": stock_text,
        "manufacturer_id": manufacturer_id,
        "manufacturer_text": manufacturer_text,
        "selling_price_type": selling_price_type,
        "selling_price_number": selling_price_number,
        "total_packs": total_packs,
        "pack_size": pack_size,
        "buying_pack_price": buying_pack_price,
        "expiration_date": expiration_date,
        "discount_type": discount_type,
        "discount_number": discount_number,
        "batch_number": batch_number
    }
    return JsonResponse({"custome_status": "", "details": details})


@login_required
@role_validator(['Data Analyst','Supervisor'])
def get_invoice_details(request):
    invoice_id = request.GET.get('invoice_id')

    invoice = Invoice.objects.get(id=int(invoice_id))
    invoice_number = invoice.invoice_number
    supplier = invoice.supplier.company_name
    date = str(invoice.date)[:10]
    paid = invoice.total_paid
    status = invoice.status
    subtotal = invoice.subtotal
    discount = invoice.total_discount
    vat = invoice.VAT_Value
    total_cost = invoice.total_cost
    balance = total_cost - paid


    details = {
        "invoice_number": invoice_number,
        "supplier": supplier,
        "date": date,
        "paid": locale.format_string('%.2f', paid, grouping=True),
        "status": status,
        "subtotal": locale.format_string('%.2f', subtotal, grouping=True),
        "discount": locale.format_string('%.2f', discount, grouping=True),
        "vat": locale.format_string('%.2f', vat, grouping=True),
        "total_cost": locale.format_string('%.2f', total_cost, grouping=True),
        "balance": locale.format_string('%.2f', balance, grouping=True)
    }

    invoice_items = InvoiceItem.objects.filter(invoice=invoice)
    if invoice_items:
        products_table = """
            <tr style="background-color:rgb(0,194,146);" class="sticky-top top-0">
                <th>#</th>
                <th>Batch #</th>
                <th>Product</th>
                <th>Pack Price</th>
                <th>Total Packs</th>
                <th>Discount</th>
                <th>VAT</th>
                <th>Total Cost</th>
            </tr>
        """
        counter = 0
        for invoice_item in invoice_items:
            counter += 1
            row = f"""
                <tr>
                    <td>{ counter }. </td>
                    <td>{ invoice_item.batch_number }</td>
                    <td>{ invoice_item.stock.product.title } <small>{ invoice_item.stock.product.details }</small> </td>
                    <td style="text-align: right">{ locale.format_string('%.2f', invoice_item.total_buying_pack_price, grouping=True) } </td>
                    <td style="text-align: right">{ locale.format_string('%.2f', invoice_item.total_packs, grouping=True) } </td>
                    <td style="text-align: right">{ locale.format_string('%.2f', invoice_item.discount_price, grouping=True) } </td>
                    <td style="text-align: right">{ locale.format_string('%.2f', invoice_item.vat_price, grouping=True) } </td>
                    <td style="text-align: right">{ locale.format_string('%.2f', invoice_item.total_cost, grouping=True) } </td>
                </tr>
            """
            products_table += row

    else:
        products_table = """
            <thead >
                <tr style="background-color:rgb(0,194,146); " class="sticky-top top-0">
                    <th style="text-align: center">No products in this invoice</th>
                </tr>
            </thead>
        """




    # invoice_money_portions = InvoiceMoneyPortion.objects.filter(invoice=invoice)
    invoice_money_portions = Payment.objects.filter(payment_for="INVOICE", payment_for_id=invoice.id)
    if invoice_money_portions:
        payments_table = """
            <tr style="background-color:rgb(0,194,146);" class="sticky-top top-0">
                <td>#</td>
                <th>Date</th>
                <th>Currency</th>
                <th style="text-align: right">Paid Amount</th>
                <th style="text-align: right">Rate</th>
                <th style="text-align: right">Paid Value</th>
                <th style="text-align: right">Manage</th>
            </tr>
        """
        counter = 0
        for invoice_money_portion in invoice_money_portions:
            counter += 1
            row = f"""
                <tr>
                    <td>{ counter }. </td>
                    <td>{ str(invoice_money_portion.date)[:10] }</td>
                    <td>{ invoice_money_portion.payment_method.shortcut }</small> </td>
                    <td style="text-align: right">{ locale.format_string('%.2f', invoice_money_portion.amount_paid, grouping=True) } </td>
                    <td style="text-align: right">{ locale.format_string('%.2f', invoice_money_portion.rate, grouping=True) } </td>
                    <td style="text-align: right">{ locale.format_string('%.2f', invoice_money_portion.rated_value, grouping=True) } </td>
                    <td style="text-align: right;"><button onclick="invoiceMoneyPortion({ invoice_money_portion.id })">🗑️</button></td>

                </tr>
            """
            payments_table += row

    else:
        payments_table = """
            <thead >
                <tr style="background-color:rgb(0,194,146); " class="sticky-top top-0">
                    <th style="text-align: center">No Payments made for this invoice</th>
                </tr>
            </thead>
        """

    return JsonResponse({"custome_status": "", "details": details, "products_table": products_table, "payments_table": payments_table})


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def get_credit_note_details(request):
    credit_note_id = request.GET.get('credit_note_id')
    credit_note = CreditNote.objects.get(id=int(credit_note_id))
    sale_transaction = credit_note.sale_transaction

    recipt_number = sale_transaction.ultimate_recipt_number
    recipt_id = sale_transaction.recipt_number
    date_bought = str(sale_transaction.created_at)[:10]
    total_units_bought = credit_note.total_units
    total_units_returned = sale_transaction.totals['total_returned']
    reason = credit_note.reason.shortcut if credit_note.reason else ""
    notes = credit_note.notes
    refund_amount = credit_note.refund_amount
    date_returned = str(credit_note.date)[:10]
    created_by = f"{credit_note.created_by.first_name.title()} {credit_note.created_by.last_name.title()}"
    created_at = str(credit_note.created_at)[:10]
    credit_note_number = credit_note.ultimate_credit_note_number
    paid_refund_value = credit_note.paid_refund_value
    status = credit_note.status
    balance = locale.format_string('%.2f', credit_note.balance, grouping=True)

    details = {
        "recipt_number": recipt_number,
        "recipt_id": recipt_id,
        "reason": reason,
        "notes": notes,
        "refund_amount": refund_amount,
        "created_by": created_by,
        "created_at": created_at,
        "total_units_bought": total_units_bought,
        "total_units_returned": total_units_returned,
        "credit_note_number": credit_note_number,
        "paid_refund_value": paid_refund_value,
        "date_bought": date_bought,
        "date_returned": date_returned,
        "balance": balance,
        "status": status,
    }

    # credit_note_refund_money_portions = RefundReturnInnMoneyPortion.objects.filter(credit_note=credit_note)
    credit_note_refund_money_portions = Payment.objects.filter(payment_for="CREDIT_NOTE", payment_for_id=credit_note.id)
    credit_note_refund_money_portions_table = """
        <tr style="background: seagreen;">
            <th>Paid By</th>
            <th>Date </th>
            <th>Currency</th>
            <th style="text-align: right;">Amount Paid</th>
            <th style="text-align: right;">Rate</th>
            <th style="text-align: right;">Paid Value</th>
            <th style="text-align: right;">🗑️</th>
        </tr>
    """
    if credit_note_refund_money_portions:
        for credit_note_refund_money_portion in credit_note_refund_money_portions:
            credit_note_refund_money_portions_table += f"""
            <tr>
                <td>{ credit_note_refund_money_portion.created_by.first_name.title() } { credit_note_refund_money_portion.created_by.last_name.title() } </td>
                <td>{ str(credit_note_refund_money_portion.date)[:10] }</td>
                <td>{ credit_note_refund_money_portion.payment_method.shortcut }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', credit_note_refund_money_portion.amount_paid, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', credit_note_refund_money_portion.rate, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', credit_note_refund_money_portion.rated_value, grouping=True) }</td>
                <td style="text-align: right;"><button onclick="deleteReturnInnRefundMoneyPortion({ credit_note_refund_money_portion.id })">🗑️</button></td>
            </tr>
            """
    else:
        credit_note_refund_money_portions_table = """
            <tr style="vertical-align: top; border-top: 1px solid #ccc;">
                <td style="text-align: center">No refund payment has been made for this return inn</td>
            </tr>
        """
    return JsonResponse({"custome_status": "", "details": details, "credit_note_refund_money_portions_table": credit_note_refund_money_portions_table})


@login_required
@role_validator(['Data Analyst','Supervisor'])
def get_return_out_details(request):
    return_out_id = request.GET.get('return_out_id')
    return_out = ReturnOut.objects.get(id=int(return_out_id))

    product_title = return_out.batch.stock.product.title
    product_details = return_out.batch.stock.product.details
    batch_number = return_out.batch.batch_number
    total_units_returned = return_out.total_units
    total_amount_refunded = return_out.refund_amount
    supplier = return_out.batch.invoice.supplier.company_name
    date_bought = str(return_out.batch.invoice.date)[:10]
    date_returned = str(return_out.date)[:10]
    return_reasons = return_out.reason.shortcut
    invoice_number = return_out.batch.invoice.invoice_number
    returned_by = f"{return_out.created_by.first_name } { return_out.created_by.last_name }"
    refund_amount = return_out.refund_amount
    refund_received = return_out.paid_refund_value
    balance = return_out.balance

    details = {
        "product_title": product_title,
        "product_details": product_details,
        "batch_number": batch_number,
        "total_units_returned": total_units_returned,
        "total_amount_refunded": total_amount_refunded,
        "supplier": supplier,
        "date_bought": date_bought,
        "date_returned": date_returned,
        "return_reasons": return_reasons,
        "invoice_number": invoice_number,
        "returned_by": returned_by,
        "refund_amount": refund_amount,
        "refund_received": refund_received,
        "balance":balance,
    }

    # return_out_refund_money_portions = RefundReturnOutMoneyPortion.objects.filter(return_out=return_out)
    return_out_refund_money_portions = Payment.objects.filter(payment_for="RETURN_OUT_REFUND", payment_for_id=return_out.id)
    return_out_refund_money_portions_table = """
        <tr style="background: seagreen;">
            <th>Paid By</th>
            <th>Date </th>
            <th>Currency</th>
            <th style="text-align: right;">Amount Paid</th>
            <th style="text-align: right;">Rate</th>
            <th style="text-align: right;">Paid Value</th>
            <th style="text-align: right;">🗑️</th>
        </tr>
    """
    if return_out_refund_money_portions:
        for return_out_refund_money_portion in return_out_refund_money_portions:
            return_out_refund_money_portions_table += f"""
            <tr>
                <td>{ return_out_refund_money_portion.created_by.first_name.title() } { return_out_refund_money_portion.created_by.last_name.title() } </td>
                <td>{ str(return_out_refund_money_portion.date)[:10] }</td>
                <td>{ return_out_refund_money_portion.payment_method.shortcut }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', return_out_refund_money_portion.amount_paid, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', return_out_refund_money_portion.rate, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', return_out_refund_money_portion.rated_value, grouping=True) }</td>
                <td style="text-align: right;"><button onclick="deleteReturnOutRefundMoneyPortion({ return_out_refund_money_portion.id })">🗑️</button></td>
            </tr>
            """
    else:
        return_out_refund_money_portions_table = """
            <tr style="vertical-align: top; border-top: 1px solid #ccc;">
                <td style="text-align: center">No refund payment has been made for this return inn</td>
            </tr>
        """


    return JsonResponse({"custome_status": "", "details": details, "return_out_refund_money_portions_table": return_out_refund_money_portions_table})



@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def get_batch_details(request):
    batch_id = request.GET.get('batch_id')
    batch = Batch.objects.get(id=int(batch_id))

    batch_number = batch.batch_number
    product_title = batch.stock.product.title
    product_details = batch.stock.product.details
    manufacturer = batch.manufacturer.company_name
    invoice_number = batch.invoice.invoice_number
    expiring = batch.expiring_in
    supplier = batch.invoice.supplier.company_name
    total_packs = batch.total_packs
    pack_size = batch.pack_size
    total_units_available = batch.total_units_available
    buying_pack_price = batch.buying_pack_price
    vat = batch.VAT
    buying_unit_price = batch.buying_unit_price
    total_units_bought = batch.total_units_bought
    expiration_date = batch.expiration_date
    status = batch.status
    received_by = f"{ batch.created_by.first_name.title() } { batch.created_by.last_name.title() }"
    date_received = str(batch.invoice.created_at)[:10]
 

    details = {
        "batch_number": batch_number,
        "product_title": product_title,
        "product_details": product_details,
        "manufacturer": manufacturer,
        "invoice_number": invoice_number,
        "expiring": expiring,
        "supplier": supplier,
        "total_units_bought": locale.format_string('%.0f', total_units_bought, grouping=True),
        "buying_unit_price": locale.format_string('%.2f', buying_unit_price, grouping=True),
        "total_packs": locale.format_string('%.0f', total_packs, grouping=True),
        "pack_size": locale.format_string('%.0f', pack_size, grouping=True),
        "total_units_available": locale.format_string('%.0f', total_units_available, grouping=True),
        "buying_pack_price": locale.format_string('%.2f', buying_pack_price, grouping=True),
        "vat": locale.format_string('%.2f', vat, grouping=True),
        "expiration_date": expiration_date,
        "status": status,
        "received_by": received_by,
        "date_received": date_received,
    }
    return JsonResponse({"details":details, "message":"New product served succesefully!"})



@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def get_stock_details(request):
    stock_id = request.GET.get('stock_id')
    stock = Stock.objects.get(id=stock_id)

    product = stock.product
    selling_price = stock.selling_price
    markup = stock.markup
    reorder_quantity = stock.reorder_quantity
    expiration_warning_days = stock.expiration_warning_days
    status = stock.status

    sales = Sale.objects.filter(stock=stock)

    sales_value = 0
    total_profit = 0
    for sale in sales:
        sales_value += float(sale.quantity * sale.buying_unit_price)
        total_profit += float(sale.selling_price - (sale.quantity * sale.buying_unit_price))

    stock_id = stock.id

    returns_inn = ReturnInn.objects.filter(stock=stock).count()

    total_sales = sales.count()
    sales_value = sales_value
    total_profit = total_profit
    returns_inn = returns_inn

    expiration_warning_days = stock.expiration_warning_days
    status = stock.status
    average_unit_cost = stock.avarage_unit_cost
    total_units = stock.total_units

    product_title = product.title
    selling_price = stock.selling_price
    markup_percentage = stock.markup

    reorder_quantity = stock.reorder_quantity
    stock_value = stock.stock_value
    to_order_status = stock.to_reorder
    product_details = stock.product.details


    details = {
        'stock_id': stock_id,

        'total_sales': locale.format_string('%.2f',total_sales, grouping=True),
        'sales_value': locale.format_string('%.2f',sales_value, grouping=True),
        'total_profit': locale.format_string('%.2f',total_profit, grouping=True),
        'returns_inn': locale.format_string('%.0f',returns_inn, grouping=True),

        'expiration_warning_days': locale.format_string('%.0f',expiration_warning_days, grouping=True),
        'status': status,
        'average_unit_cost': locale.format_string('%.2f',average_unit_cost, grouping=True),
        'total_units': locale.format_string('%.0f',total_units, grouping=True),

        'product_title': product_title,
        'selling_price': locale.format_string('%.2f',selling_price, grouping=True),
        'markup_percentage': locale.format_string('%.2f',markup_percentage, grouping=True),

        'reorder_quantity': locale.format_string('%.0f',reorder_quantity, grouping=True),
        'stock_value': locale.format_string('%.2f',stock_value, grouping=True),
        'to_order_status': to_order_status,
        'product_details': product_details
    }
    return JsonResponse({"details":details, "message":"New product served succesefully!"})


#   add


@login_required
@role_validator(['Supervisor'])
@transaction.atomic
def add_batch_invoice_patching(request):
    invoice_id = request.GET.get('invoice_id')
    stock_id = request.GET.get('stock_id')
    payment_instruction = request.GET.get('payment_instruction')
    manufacturer = request.GET.get('manufacturer')
    selling_price_type = request.GET.get('selling_price_type')
    selling_price_number = Decimal(request.GET.get('selling_price_number'))
    expiration_date = request.GET.get('expiration_date')
    total_packs = Decimal(request.GET.get('total_packs'))
    pack_size = Decimal(request.GET.get('pack_size'))
    buying_pack_price = Decimal(request.GET.get('pack_price'))
    batch_number = request.GET.get('batch_number')
    discount_type = request.GET.get('discount_type')
    discount_number = Decimal(request.GET.get('discount_number'))


    try:
        invoice = Invoice.objects.get(id=int(invoice_id))
        stock = Stock.objects.get(id=int(stock_id))
        manufacturer = Manufacturer.objects.get(id=int(stock_id))
    except Exception as e:
        return JsonResponse({'title': "Error", 'text': str(e), 'type': "error"})
        
    vat_price = Decimal(stock.product.vat_code.percentage) * Decimal(0.01) * total_packs * buying_pack_price
    vat_percentage = Decimal(stock.product.vat_code.percentage) * Decimal(0.01)

    if discount_type == "DISCOUNT PERCENTAGE":
        discount_price = (total_packs * buying_pack_price) * (discount_number * Decimal(0.01))
        print('discount_price')
        print(discount_price)
        discount_percentage = discount_number

    elif discount_type == "DISCOUNT PRICE":
        discount_price = discount_number
        discount_percentage = (discount_number * Decimal(0.01)) * (total_packs * buying_pack_price)
    else:
        message = "You can not use the selected discount type."
        return JsonResponse({'title': "Error", 'text': message, 'type': "error"})


    total_buying_pack_price = buying_pack_price #- discount_price
   
    if selling_price_type == "MARKUP PERCENTAGE":
        markup = selling_price_number
        buying_unit_cost = buying_pack_price / pack_size
        selling_price = (markup / 100) * buying_unit_cost + buying_unit_cost 
        

    elif selling_price_type == "SELLING PRICE":
        selling_price = selling_price_number
        buying_unit_cost = buying_pack_price / pack_size
        markup = (selling_price - buying_unit_cost)/(buying_unit_cost)*100
    elif selling_price_type == "EXISTING PRICE":
        try:
            markup = stock.markup
            selling_price = stock.selling_price
        except Exception as e:
            return JsonResponse({'title': "Error", 'text': "Error! You do not have an existing price  for this stock yet", 'type': "error"})
        
    else:
        message = "You can not use the selected markup type."
        return JsonResponse({'title': "Error", 'text': message, 'type': "error"})
        

    stock.selling_price = selling_price
    stock.markup = markup
    stock.save()


    # create invoice item
    new_invoice_item = InvoiceItem()
    new_invoice_item.invoice = invoice
    new_invoice_item.stock = stock
    new_invoice_item.manufacturer = manufacturer
    new_invoice_item.vat_price = vat_price
    new_invoice_item.vat_percentage = vat_percentage
    new_invoice_item.discount_price = discount_price
    new_invoice_item.discount_percentage = discount_percentage
    new_invoice_item.total_packs = total_packs
    new_invoice_item.pack_size = pack_size 
    new_invoice_item.buying_pack_price = buying_pack_price
    new_invoice_item.total_buying_pack_price = total_buying_pack_price
    new_invoice_item.markup = markup
    new_invoice_item.selling_price = selling_price
    new_invoice_item.expiration_date = expiration_date
    new_invoice_item.batch_number = batch_number
    new_invoice_item.save()

    # create batch
    new_batch = Batch()
    new_batch.batch_number = new_invoice_item.batch_number
    new_batch.stock = new_invoice_item.stock
    new_batch.manufacturer = new_invoice_item.manufacturer
    new_batch.invoice = new_invoice_item.invoice
    new_batch.total_packs = new_invoice_item.total_packs
    new_batch.pack_size = new_invoice_item.pack_size
    new_batch.total_units = new_invoice_item.pack_size * new_invoice_item.total_packs
    new_batch.buying_pack_price = new_invoice_item.buying_pack_price
    new_batch.VAT = new_invoice_item.discount_price
    new_batch.markup = new_invoice_item.markup
    new_batch.expiration_date = new_invoice_item.expiration_date
    new_batch.created_by = request.user

    new_batch.save()


    content = f"New independent batch, Batch ID: { new_batch.id }, { new_batch.total_units } units added to INVOICE NUMBER { invoice.invoice_number}. SELLING PRICE: type: { selling_price_type }, price: { selling_price_type }, markup: { markup }"
    log_activity(content, request.user)


    # take care of payment
    if payment_instruction == "AUTO":
        payments = Payment.objects.filter(payment_for="INVOICE", payment_for_id=invoice.id)
        if payments:
            dominant_payment = payments.first()
            dominant_payment_method = dominant_payment.payment_method

            amount_paid = Decimal(new_invoice_item.subtotal) * Decimal(dominant_payment.rate)
            dominant_payment.amount_paid += amount_paid
            dominant_payment.save()

            content = f"PAYMENT: { dominant_payment_method.shortcut } { locale.format_string('%.0f', amount_paid, grouping=True) } @ { locale.format_string('%.0f', dominant_payment.rate, grouping=True) } rate."
            log_activity(content, request.user)
        else:
            content = f"PAYMENT: No payment recorded"
            log_activity(content, request.user)
            return JsonResponse({'title': "Added", 'text': "Batch added succesefully, but you need to take care of the payment manualy in invoices", 'type': "info"})




    return JsonResponse({'title': "Added", 'text': "Batch added succesefully", 'type': "success"})





import logging
import json
import threading
from datetime import datetime
from decimal import Decimal
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from fiscalisation.models import FiscalisationSettings, FiscalReceipt
from fiscalisation.services import create_fiscal_receipt, sync_receipt

logger = logging.getLogger(__name__)


def return_inn_sale_bulk(request):
    OLD_PRINT = os.getenv("OLD_PRINT", "false").lower() == "true"
    if OLD_PRINT:
        return return_inn_sale_bulk_old(request)

    else:
        return return_inn_sale_bulk_new(request)




@login_required
@role_validator(['Sales Rep'])
# @transaction.atomic
def return_inn_sale_bulk_new(request):
    """
    Complete bulk return with fiscalisation support.
    ALL database operations are atomic - either all succeed or all fail.
    """
    try:
        # ============================================================
        # STEP 1: Get POST data
        # ============================================================
        receipt_number = request.POST.get('receipt_number')
        return_date = request.POST.get('return_date')
        return_reason = request.POST.get('return_reason')
        refund_amount = request.POST.get('refund_amount')
        payment_method_id = request.POST.get('payment_method')
        amount_paid = request.POST.get('amount_paid')
        tableData = json.loads(request.POST.get('tableData', '[]'))

        # ============================================================
        # STEP 2: Get the original sale transaction
        # ============================================================
        original_sale = SaleTransaction.objects.get(recipt_number=int(receipt_number))
        sale_payments = Payment.objects.filter(payment_for="RECEIPT", payment_for_id=receipt_number)
        
        # ============================================================
        # STEP 3: Check conditions to fiscalise credit note
        # ============================================================
        # -invoice fiscalise
        # -1 payment method
        # -same payment method as invoice
        # -same rate as invoice
        original_fiscal_receipt = FiscalReceipt.objects.filter(
            local_receipt_number=str(receipt_number),
            doc_type='FISCALINVOICE'
        ).first()

        should_fiscalise_return = original_fiscal_receipt is not None
        fiscal_settings = FiscalisationSettings.get_settings()
        
        if not original_fiscal_receipt:
            logger.warning(f"Original sale {receipt_number} was not fiscalised. Return will NOT be fiscalised.")
        
        payment_method = PaymentMethod.objects.get(id=int(payment_method_id))
        
        # ============================================================
        # STEP 4: Create Credit Note record
        # ============================================================
        new_credit_note = CreditNote()
        new_credit_note.sale_transaction = original_sale
        new_credit_note.reason = ReturnReason.objects.get(id=int(return_reason))
        new_credit_note.notes = ""
        new_credit_note.refund_amount = Decimal(str(refund_amount))
        new_credit_note.date = return_date
        new_credit_note.created_by = request.user
        new_credit_note.save()
        credit_note = new_credit_note

        # ============================================================
        # STEP 5: Process returned items and calculate totals
        # ============================================================
        no_items_selected = True
        credit_note_lines = []
        total_credit_incl_vat = Decimal('0')
        total_refund_amount = Decimal('0')

        # Tax accumulators (will be negative for credit note)
        document_total = Decimal('0')
        nontaxible_sales_amt_total = Decimal('0')
        zero_per_taxamt = Decimal('0')
        zero_perc_sales_amt_total = Decimal('0')
        tax_amt_15_perc = Decimal('0')
        tax_15_perc_sales_total = Decimal('0')

        for sale_data in tableData:
            no_items_selected = False
            sale = Sale.objects.get(id=int(sale_data['id']))
            return_quantity = int(sale_data['return_quantity'])
            
            if return_quantity <= 0:
                continue
                
            if sale.actual_sales < return_quantity:
                return_quantity = sale.actual_sales
            
            # Update sale return totals
            sale.total_returned += return_quantity
            sale.save()
            
            # Return items to batches (stock) - existing code
            used_batches = sale.used_batches.rstrip(",") if sale.used_batches else ""
            used_batch_quantities = sale.used_batch_quantities.rstrip(",") if sale.used_batch_quantities else ""
            
            if used_batches and used_batch_quantities:
                used_batches_list = used_batches.split(",")
                used_batch_quantities_list = used_batch_quantities.split(",")
                
                used_batches_list_int = [int(b) for b in used_batches_list if b]
                used_batch_quantities_list_int = [int(q) for q in used_batch_quantities_list if q]
                
                used_batches_list_int.reverse()
                used_batch_quantities_list_int.reverse()
                
                remaining_needed = return_quantity
                still_needed = True
                
                for i in range(len(used_batches_list_int)):
                    if still_needed:
                        current_batch = Batch.objects.get(id=used_batches_list_int[i])
                        current_batch_used_quantity = used_batch_quantities_list_int[i]
                        
                        if current_batch_used_quantity - remaining_needed >= 0:
                            current_batch.total_units = int(current_batch.total_units) + remaining_needed
                            current_batch.save()
                            used_batch_quantities_list_int[i] = current_batch_used_quantity - remaining_needed
                            still_needed = False
                        else:
                            current_batch.total_units = int(current_batch.total_units) + current_batch_used_quantity
                            current_batch.save()
                            remaining_needed -= current_batch_used_quantity
                            used_batches_list_int[i] = 0
                            used_batch_quantities_list_int[i] = 0
                
                filtered_batches = []
                filtered_quantities = []
                for i in range(len(used_batches_list_int)):
                    if used_batches_list_int[i] != 0:
                        filtered_batches.append(str(used_batches_list_int[i]))
                        filtered_quantities.append(str(used_batch_quantities_list_int[i]))
                
                filtered_batches.reverse()
                filtered_quantities.reverse()
                
                sale.used_batches = ",".join(filtered_batches)
                sale.used_batch_quantities = ",".join(filtered_quantities)
                sale.save()
            
            # ============================================================
            # Calculate prices for credit note
            # ============================================================
            price_incl_vat = Decimal(str(sale.unit_price))
            quantity = Decimal(str(return_quantity))
            rate = Decimal(str(payment_method.rate))
            
            # Get VAT percentage
            vat_percentage = 0
            int_tax_code = 2  # Default Zero%
            
            if sale.stock.product.vat_code:
                int_tax_code = sale.stock.product.vat_code.zimra_tax_id or 2
                vat_percentage = Decimal(str(sale.stock.product.vat_code.percentage or 0))
                if vat_percentage == 15:
                    vat_percentage = 15.5
                    int_tax_code = 517
            
            # Calculate line total (POSITIVE amount)
            line_total_incl_vat = Decimal(str(price_incl_vat * quantity * rate))
            
            # Accumulate total refund amount
            total_refund_amount += Decimal(str(line_total_incl_vat))
            
            # Determine tax code and accumulate
            if int_tax_code == 1:  # Exempt
                str_tax_code = "A"
                tax_percentage = ""
                nontaxible_sales_amt_total += line_total_incl_vat

            elif int_tax_code == 2:  # Zero %
                str_tax_code = "B"
                tax_percentage = str(round(0, 2))
                zero_perc_sales_amt_total += line_total_incl_vat

            elif int_tax_code == 3:  # 15% VAT Inclusive
                str_tax_code = "C"
                tax_percentage = str(round(15, 2))
                tax_amt_15_perc += Decimal(str(15 / 115)) * Decimal(str(line_total_incl_vat))
                tax_15_perc_sales_total += line_total_incl_vat

            elif int_tax_code == 4 or int_tax_code == 517:  # 15.5% VAT Inclusive
                int_tax_code = 517
                str_tax_code = "D"
                tax_percentage = str(round(15.5, 2))
                tax_amt_15_perc += Decimal(str(15.5 / 115.5)) * Decimal(str(line_total_incl_vat))
                tax_15_perc_sales_total += line_total_incl_vat

            else:
                str_tax_code = "B"
                tax_percentage = str(round(0, 2))
                zero_perc_sales_amt_total += line_total_incl_vat

            # Accumulate total credit
            total_credit_incl_vat += Decimal(str(line_total_incl_vat))

            # Get HS code
            hs_code = sale.stock.product.zimra_hs_code
            if not is_correct_hs_code_format(str(hs_code)):
                hs_code = sale.stock.product.vat_code.default_hs_code
                if not is_correct_hs_code_format(str(hs_code)):
                    hs_code = '95069100'
            
            # Add to credit note lines (NEGATIVE for credit note)
            credit_note_lines.append({
                "LineDescription": f"{sale.stock.product.title} {sale.stock.product.details}",
                "UnitPrice": str(round(-price_incl_vat * rate, 2)),
                "Quantity": str(quantity),
                "Total": str(round(-line_total_incl_vat, 2)),
                "IntTaxCode": int_tax_code,
                "StrTaxCode": str_tax_code,
                "TaxPercentage": tax_percentage,
                "receiptLineHSCode": hs_code,
            })

            # Create ReturnInn record
            new_return_inn = ReturnInn()
            new_return_inn.credit_note = credit_note
            new_return_inn.sale = sale
            new_return_inn.stock = sale.stock
            new_return_inn.refund_amount = 0
            new_return_inn.total_units = return_quantity
            new_return_inn.sale_value = line_total_incl_vat
            new_return_inn.created_by = request.user
            new_return_inn.save()
        
        if no_items_selected:
            return JsonResponse({
                "custome_status": "", 
                "message": "Nothing returned inn. The given items have been returned already or you're trying to return zero items."
            })
        
        # ============================================================
        # STEP 6: Create refund payment record
        # ============================================================
        payments_list = []

        # Use the calculated total refund amount, not the POSTed amount
        refund_total = float(total_refund_amount)
        
        if refund_total > 0:
            refund_payment = Payment()
            refund_payment.payment_for = "CREDIT_NOTE"
            refund_payment.payment_for_id = credit_note.id
            refund_payment.payment_method = payment_method
            refund_payment.date = datetime.today()
            refund_payment.rate = payment_method.rate
            refund_payment.amount_paid = Decimal(str(refund_total))
            refund_payment.created_by = request.user
            refund_payment.save()

            payments_list.append({
                "PaymentMethodName": refund_payment.payment_method.zimra_money_type_text.upper(),
                "PaymentAmt": str(-round(refund_total, 2)),
            })
        else:
            # If no refund amount, add a zero payment
            payments_list.append({
                "PaymentMethodName": payment_method.zimra_money_type_text.upper(),
                "PaymentAmt": "0.00",
            })

        # ============================================================
        # STEP 7: Make totals NEGATIVE for credit note
        # ============================================================
        document_total = -total_credit_incl_vat
        nontaxible_sales_amt_total = -nontaxible_sales_amt_total
        zero_per_taxamt = -zero_per_taxamt
        zero_perc_sales_amt_total = -zero_perc_sales_amt_total
        tax_amt_15_perc = -tax_amt_15_perc
        tax_15_perc_sales_total = -tax_15_perc_sales_total

        # ============================================================
        # STEP 8: Create FISCAL CREDIT NOTE (ONLY if original was fiscalised)
        # ============================================================
        qr_url = ""
        fiscal_credit_note = None
        
        sale_transaction = credit_note.sale_transaction

        if should_fiscalise_return and original_fiscal_receipt:
            the_password = ""
            role = ""
            payment_lines = payments_list
            line_items = credit_note_lines
            doc_type = "CREDITNOTE"
            doc_currency = payment_method.shortcut.upper()
            my_yyy_mm_dd_date = credit_note.created_at.strftime('%Y-%m-%d')
            my_24hr_time_format_with_seconds = credit_note.created_at.strftime('%H:%M:%S')
            invoice_number_to_credit_debit = original_fiscal_receipt.inv_number
            local_invoice_number_to_credit_debit = credit_note.id
            
            buyer_register_name = sale_transaction.buyer_name or "Walk In Customer"
            buyer_TIN = sale_transaction.buyer_tin or ""
            VAT_number = sale_transaction.buyer_vat or "" 
            phone_no = sale_transaction.buyer_tel or "" 
            email = sale_transaction.buyer_email or "" 
            local_receipt_number = sale_transaction.recipt_number
            status = "PENDING"

            fiscal_credit_note = create_fiscal_receipt(
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

            # Start background sync
            from fiscalisation.services import sync_receipt_async
            sync_receipt_async(fiscal_credit_note.id)

            # time.sleep(configuration.print_delay)
            
            
            # if fiscal_credit_note.qr_code_url:
            #     qr_url = fiscal_credit_note.qr_code_url
            
        else:
            logger.info(f"Original sale {receipt_number} was NOT fiscalised. Skipping fiscal credit note.")
        
        # ============================================================
        # STEP 9: Print credit note
        # ============================================================
        printer = get_printer(request)




        def _print():
            try:
                if should_fiscalise_return:
                    time.sleep(configuration.print_delay)
                else:
                    pass #no fiscalisation no delay
                print_this_document(request, printer, "CREDITNOTE", credit_note.id, "(COPY)")
                print_this_document(request, printer, "CREDITNOTE", credit_note.id, "")
            except Exception:
                logger.exception("Receipt reprint failed")

        threading.Thread(target=_print, daemon=True).start()
        
        return JsonResponse({
            "custome_status": "", 
            "message": f"Product(s) returned in stock successfully!<br>{message}",
        })
        
    except Exception as e:
        logger.exception("Return failed")
        return JsonResponse({
            "custome_status": "Error", 
            "message": str(e)
        })





@login_required
@role_validator(['Sales Rep'])
@transaction.atomic
def return_inn_sale_bulk_old(request):
    """
    Complete bulk return with fiscalisation support.
    ALL database operations are atomic - either all succeed or all fail.
    """
    try:
        # ============================================================
        # STEP 1: Get POST data
        # ============================================================
        receipt_number = request.POST.get('receipt_number')
        return_date = request.POST.get('return_date')
        return_reason = request.POST.get('return_reason')
        refund_amount = request.POST.get('refund_amount')
        payment_method_id = request.POST.get('payment_method')
        amount_paid = request.POST.get('amount_paid')
        tableData = json.loads(request.POST.get('tableData', '[]'))

        # ============================================================
        # STEP 2: Get the original sale transaction
        # ============================================================
        original_sale = SaleTransaction.objects.get(recipt_number=int(receipt_number))
        sale_payments = Payment.objects.filter(payment_for="RECEIPT", payment_for_id=receipt_number)
        
        # ============================================================
        # STEP 3: Check conditions to fiscalise credit note
        # ============================================================
        # -invoice fiscalise
        # -1 payment method
        # -same payment method as invoice
        # -same rate as invoice
        original_fiscal_receipt = FiscalReceipt.objects.filter(
            local_receipt_number=str(receipt_number),
            doc_type='FISCALINVOICE'
        ).first()

        should_fiscalise_return = original_fiscal_receipt is not None
        fiscal_settings = FiscalisationSettings.get_settings()
        
        if not original_fiscal_receipt:
            logger.warning(f"Original sale {receipt_number} was not fiscalised. Return will NOT be fiscalised.")
        
        payment_method = PaymentMethod.objects.get(id=int(payment_method_id))
        
        # ============================================================
        # STEP 4: Create Credit Note record
        # ============================================================
        new_credit_note = CreditNote()
        new_credit_note.sale_transaction = original_sale
        new_credit_note.reason = ReturnReason.objects.get(id=int(return_reason))
        new_credit_note.notes = ""
        new_credit_note.refund_amount = Decimal(str(refund_amount))
        new_credit_note.date = return_date
        new_credit_note.created_by = request.user
        new_credit_note.save()
        credit_note = new_credit_note

        # ============================================================
        # STEP 5: Process returned items and calculate totals
        # ============================================================
        no_items_selected = True
        credit_note_lines = []
        total_credit_incl_vat = Decimal('0')
        total_refund_amount = Decimal('0')

        # Tax accumulators (will be negative for credit note)
        document_total = Decimal('0')
        nontaxible_sales_amt_total = Decimal('0')
        zero_per_taxamt = Decimal('0')
        zero_perc_sales_amt_total = Decimal('0')
        tax_amt_15_perc = Decimal('0')
        tax_15_perc_sales_total = Decimal('0')

        for sale_data in tableData:
            no_items_selected = False
            sale = Sale.objects.get(id=int(sale_data['id']))
            return_quantity = int(sale_data['return_quantity'])
            
            if return_quantity <= 0:
                continue
                
            if sale.actual_sales < return_quantity:
                return_quantity = sale.actual_sales
            
            # Update sale return totals
            sale.total_returned += return_quantity
            sale.save()
            
            # Return items to batches (stock) - existing code
            used_batches = sale.used_batches.rstrip(",") if sale.used_batches else ""
            used_batch_quantities = sale.used_batch_quantities.rstrip(",") if sale.used_batch_quantities else ""
            
            if used_batches and used_batch_quantities:
                used_batches_list = used_batches.split(",")
                used_batch_quantities_list = used_batch_quantities.split(",")
                
                used_batches_list_int = [int(b) for b in used_batches_list if b]
                used_batch_quantities_list_int = [int(q) for q in used_batch_quantities_list if q]
                
                used_batches_list_int.reverse()
                used_batch_quantities_list_int.reverse()
                
                remaining_needed = return_quantity
                still_needed = True
                
                for i in range(len(used_batches_list_int)):
                    if still_needed:
                        current_batch = Batch.objects.get(id=used_batches_list_int[i])
                        current_batch_used_quantity = used_batch_quantities_list_int[i]
                        
                        if current_batch_used_quantity - remaining_needed >= 0:
                            current_batch.total_units = int(current_batch.total_units) + remaining_needed
                            current_batch.save()
                            used_batch_quantities_list_int[i] = current_batch_used_quantity - remaining_needed
                            still_needed = False
                        else:
                            current_batch.total_units = int(current_batch.total_units) + current_batch_used_quantity
                            current_batch.save()
                            remaining_needed -= current_batch_used_quantity
                            used_batches_list_int[i] = 0
                            used_batch_quantities_list_int[i] = 0
                
                filtered_batches = []
                filtered_quantities = []
                for i in range(len(used_batches_list_int)):
                    if used_batches_list_int[i] != 0:
                        filtered_batches.append(str(used_batches_list_int[i]))
                        filtered_quantities.append(str(used_batch_quantities_list_int[i]))
                
                filtered_batches.reverse()
                filtered_quantities.reverse()
                
                sale.used_batches = ",".join(filtered_batches)
                sale.used_batch_quantities = ",".join(filtered_quantities)
                sale.save()
            
            # ============================================================
            # Calculate prices for credit note
            # ============================================================
            price_incl_vat = Decimal(str(sale.unit_price))
            quantity = Decimal(str(return_quantity))
            rate = Decimal(str(payment_method.rate))
            
            # Get VAT percentage
            vat_percentage = 0
            int_tax_code = 2  # Default Zero%
            
            if sale.stock.product.vat_code:
                int_tax_code = sale.stock.product.vat_code.zimra_tax_id or 2
                vat_percentage = Decimal(str(sale.stock.product.vat_code.percentage or 0))
                if vat_percentage == 15:
                    vat_percentage = 15.5
                    int_tax_code = 517
            
            # Calculate line total (POSITIVE amount)
            line_total_incl_vat = Decimal(str(price_incl_vat * quantity * rate))
            
            # Accumulate total refund amount
            total_refund_amount += Decimal(str(line_total_incl_vat))
            
            # Determine tax code and accumulate
            if int_tax_code == 1:  # Exempt
                str_tax_code = "A"
                tax_percentage = ""
                nontaxible_sales_amt_total += line_total_incl_vat

            elif int_tax_code == 2:  # Zero %
                str_tax_code = "B"
                tax_percentage = str(round(0, 2))
                zero_perc_sales_amt_total += line_total_incl_vat

            elif int_tax_code == 3:  # 15% VAT Inclusive
                str_tax_code = "C"
                tax_percentage = str(round(15, 2))
                tax_amt_15_perc += Decimal(str(15 / 115)) * Decimal(str(line_total_incl_vat))
                tax_15_perc_sales_total += line_total_incl_vat

            elif int_tax_code == 4 or int_tax_code == 517:  # 15.5% VAT Inclusive
                int_tax_code = 517
                str_tax_code = "D"
                tax_percentage = str(round(15.5, 2))
                tax_amt_15_perc += Decimal(str(15.5 / 115.5)) * Decimal(str(line_total_incl_vat))
                tax_15_perc_sales_total += line_total_incl_vat

            else:
                str_tax_code = "B"
                tax_percentage = str(round(0, 2))
                zero_perc_sales_amt_total += line_total_incl_vat

            # Accumulate total credit
            total_credit_incl_vat += Decimal(str(line_total_incl_vat))

            # Get HS code
            hs_code = sale.stock.product.zimra_hs_code
            if not is_correct_hs_code_format(str(hs_code)):
                hs_code = sale.stock.product.vat_code.default_hs_code
                if not is_correct_hs_code_format(str(hs_code)):
                    hs_code = '95069100'
            
            # Add to credit note lines (NEGATIVE for credit note)
            credit_note_lines.append({
                "LineDescription": f"{sale.stock.product.title} {sale.stock.product.details}",
                "UnitPrice": str(round(-price_incl_vat * rate, 2)),
                "Quantity": str(quantity),
                "Total": str(round(-line_total_incl_vat, 2)),
                "IntTaxCode": int_tax_code,
                "StrTaxCode": str_tax_code,
                "TaxPercentage": tax_percentage,
                "receiptLineHSCode": hs_code,
            })

            # Create ReturnInn record
            new_return_inn = ReturnInn()
            new_return_inn.credit_note = credit_note
            new_return_inn.sale = sale
            new_return_inn.stock = sale.stock
            new_return_inn.refund_amount = 0
            new_return_inn.total_units = return_quantity
            new_return_inn.sale_value = line_total_incl_vat
            new_return_inn.created_by = request.user
            new_return_inn.save()
        
        if no_items_selected:
            return JsonResponse({
                "custome_status": "", 
                "message": "Nothing returned inn. The given items have been returned already or you're trying to return zero items."
            })
        
        # ============================================================
        # STEP 6: Create refund payment record
        # ============================================================
        payments_list = []

        # Use the calculated total refund amount, not the POSTed amount
        refund_total = float(total_refund_amount)
        
        if refund_total > 0:
            refund_payment = Payment()
            refund_payment.payment_for = "CREDIT_NOTE"
            refund_payment.payment_for_id = credit_note.id
            refund_payment.payment_method = payment_method
            refund_payment.date = datetime.today()
            refund_payment.rate = payment_method.rate
            refund_payment.amount_paid = Decimal(str(refund_total))
            refund_payment.created_by = request.user
            refund_payment.save()

            payments_list.append({
                "PaymentMethodName": refund_payment.payment_method.zimra_money_type_text.upper(),
                "PaymentAmt": str(-round(refund_total, 2)),
            })
        else:
            # If no refund amount, add a zero payment
            payments_list.append({
                "PaymentMethodName": payment_method.zimra_money_type_text.upper(),
                "PaymentAmt": "0.00",
            })

        # ============================================================
        # STEP 7: Make totals NEGATIVE for credit note
        # ============================================================
        document_total = -total_credit_incl_vat
        nontaxible_sales_amt_total = -nontaxible_sales_amt_total
        zero_per_taxamt = -zero_per_taxamt
        zero_perc_sales_amt_total = -zero_perc_sales_amt_total
        tax_amt_15_perc = -tax_amt_15_perc
        tax_15_perc_sales_total = -tax_15_perc_sales_total

        # ============================================================
        # STEP 8: Create FISCAL CREDIT NOTE (ONLY if original was fiscalised)
        # ============================================================
        qr_url = ""
        fiscal_credit_note = None
        
        sale_transaction = credit_note.sale_transaction

        if should_fiscalise_return and original_fiscal_receipt:
            the_password = ""
            role = ""
            payment_lines = payments_list
            line_items = credit_note_lines
            doc_type = "CREDITNOTE"
            doc_currency = payment_method.shortcut.upper()
            my_yyy_mm_dd_date = credit_note.created_at.strftime('%Y-%m-%d')
            my_24hr_time_format_with_seconds = credit_note.created_at.strftime('%H:%M:%S')
            invoice_number_to_credit_debit = original_fiscal_receipt.inv_number
            local_invoice_number_to_credit_debit = credit_note.id
            
            buyer_register_name = sale_transaction.buyer_name or "Walk In Customer"
            buyer_TIN = sale_transaction.buyer_tin or ""
            VAT_number = sale_transaction.buyer_vat or "" 
            phone_no = sale_transaction.buyer_tel or "" 
            email = sale_transaction.buyer_email or "" 
            local_receipt_number = sale_transaction.recipt_number
            status = "PENDING"

            fiscal_credit_note = create_fiscal_receipt(
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

            # Start background sync
            from fiscalisation.services import sync_receipt_async
            sync_receipt_async(fiscal_credit_note.id)
            
            logger.info(f"Fiscal credit note created for return of fiscalised sale {receipt_number}")
            
            if fiscal_credit_note.qr_code_url:
                qr_url = fiscal_credit_note.qr_code_url
            
        else:
            logger.info(f"Original sale {receipt_number} was NOT fiscalised. Skipping fiscal credit note.")
        
        # ============================================================
        # STEP 9: Print credit note
        # ============================================================
        fiscal_device_id = fiscal_settings.device_id if should_fiscalise_return else None
        custome_status, message = print_out_credit_note_bulk(
            receipt_number, 
            credit_note.id, 
            " ", 
            qr_url, 
            fiscal_device_id
        )
        print_out_credit_note_bulk(
            receipt_number, 
            credit_note.id, 
            "COPY", 
            qr_url, 
            fiscal_device_id
        )
        
        return JsonResponse({
            "custome_status": "", 
            "message": f"Product(s) returned in stock successfully!<br>{message}",
            "return_inn_id": str(credit_note.id),
            "qr_code": qr_url,
            "fiscal_credit_note_id": fiscal_credit_note.id if fiscal_credit_note else None,
            "was_fiscalised": should_fiscalise_return,
        })
        
    except Exception as e:
        logger.exception("Return failed")
        return JsonResponse({
            "custome_status": "Error", 
            "message": str(e)
        })


@login_required
@role_validator(['Sales Rep'])
def return_inn_sale(request):
    # sale_id = request.GET.get('sale_id')
    # date_returned = request.GET.get('date_returned')
    # refund_amount = request.GET.get('refund_amount')
    # total_units = request.GET.get('total_units')
    # return_reason = request.GET.get('return_reason')
    # amount_paid = float(request.GET.get('amount_paid'))
    # payment_method = request.GET.get('payment_method')

    # sale = Sale.objects.get(id=int(sale_id))
    # if sale.actual_sales < int(total_units):
    #     return JsonResponse({"custome_status": "Error", "message":f"You can not return more units than sold. Only {sale.actual_sales} were sold!"})
    # else:
    #     #subtract from bachies
    #     used_batches = sale.used_batches.rstrip(",")
    #     used_batch_quantities = sale.used_batch_quantities.rstrip(",")
    #     sale.total_returned += int(total_units)
    #     # print(used_batches)


    #     # .reverse() to return the lastly collected batches
    #     used_batches_list = used_batches.split(",")
    #     used_batch_quantities_list = used_batch_quantities.split(",")
    #     # print(used_batches_list)

    #     used_batches_list.reverse()
    #     used_batch_quantities_list.reverse()
    #     # print(used_batches_list)

    #     total_returnable_units = 0
    #     if used_batch_quantities_list[0] != "":
    #         for i in range(len(used_batch_quantities_list)):
    #             total_returnable_units += int(used_batch_quantities_list[i])

    #     remaining_needed = int(total_units)
    #     still_needed = True
    #     for i in range(len(used_batches_list)):
    #         if still_needed:
    #             if used_batches_list[i] == "":
    #                 return JsonResponse({"custome_status": "Error", "message":f"You have returned inn all items in this sale!"})

    #             if  remaining_needed > total_returnable_units:
    #                 return JsonResponse({"custome_status": "Error", "message":f"You can only return inn { total_returnable_units } unit(s) on this sale!"})


    #             current_batch = Batch.objects.get(id=int(used_batches_list[i]))
    #             current_batch_used_quantity = int(used_batch_quantities_list[i])

    #             if current_batch_used_quantity - remaining_needed == 0:
    #                 # enough and remaining 0 batches used
    #                 current_batch.total_units = int(current_batch.total_units) + current_batch_used_quantity
    #                 current_batch.save()
                   
    #                 # alterartions and saving
    #                 del used_batches_list[i]
    #                 del used_batch_quantities_list[i]

    #                 used_batches_list.reverse()
    #                 used_batch_quantities_list.reverse()
                    
    #                 sale.used_batches = ",".join(map(str, used_batches_list))
    #                 sale.used_batch_quantities = ",".join(map(str, used_batch_quantities_list))
    #                 sale.save()

    #                 still_needed = False

    #             elif current_batch_used_quantity - remaining_needed > 0:
    #                 #enough current_batch_used_quantity and remainder in that batch
    #                 current_batch.total_units = int(current_batch.total_units) + current_batch_used_quantity
    #                 current_batch.save()

    #                 # alterartions and saving
    #                 #used_batches_list[i] remains the same
    #                 used_batch_quantities_list[i] = current_batch_used_quantity - remaining_needed

    #                 used_batches_list.reverse()
    #                 used_batch_quantities_list.reverse()
                    
    #                 sale.used_batches = ",".join(map(str, used_batches_list))
    #                 sale.used_batch_quantities = ",".join(map(str, used_batch_quantities_list))
    #                 sale.save()

    #                 still_needed = False

    #             else:
    #                 #there is not enough current_batch_used_quantity in that batch
    #                 current_batch.total_units = int(current_batch.total_units) + current_batch_used_quantity
    #                 current_batch.save()

    #                 # alterartions and saving
    #                 del used_batches_list[i]
    #                 del used_batch_quantities_list[i]

    #                 used_batches_list.reverse()
    #                 used_batch_quantities_list.reverse()
                    
    #                 sale.used_batches = ",".join(map(str, used_batches_list))
    #                 sale.used_batch_quantities = ",".join(map(str, used_batch_quantities_list))
    #                 sale.save()

    #                 remaining_needed = remaining_needed - current_batch_used_quantity

    #     new_return_inn = ReturnInn()
    #     new_return_inn.sale = sale
    #     new_return_inn.stock = sale.stock
    #     new_return_inn.reason = ReturnReason.objects.get(id=int(return_reason))
    #     new_return_inn.refund_amount = refund_amount
    #     new_return_inn.total_units = total_units
    #     new_return_inn.sale_value = (sale.unit_price + sale.VAT) * total_units
    #     new_return_inn.created_by = request.user
    #     new_return_inn.save()

    #     try:
    #         payment_method = PaymentMethod.objects.get(id=int(payment_method))
    #         if amount_paid != 0:
    #             # new_refund_return_inn_money_portion = RefundReturnInnMoneyPortion()
    #             new_refund_return_inn_money_portion = Payment()
    #             new_refund_return_inn_money_portion.payment_for = "CREDIT_NOTE"
    #             new_refund_return_inn_money_portion.return_inn = new_return_inn
    #             new_refund_return_inn_money_portion.payment_method = payment_method
    #             new_refund_return_inn_money_portion.rate = payment_method.rate
    #             new_refund_return_inn_money_portion.amount_paid = amount_paid
    #             new_refund_return_inn_money_portion.created_by = request.user
    #             new_refund_return_inn_money_portion.save()
        
    #     except:
    #         pass
    
    return JsonResponse({"custome_status": "", "message":"Product(s) returned in stock succesefully!", "return_inn_id":str(new_return_inn.id)})

@role_validator(['Supervisor'])
def add_return_reason(request):
    shortcut = request.GET.get('shortcut')
    details = request.GET.get('details')

    already_exist = ReturnReason.objects.filter(shortcut__iexact=shortcut)
    if already_exist:
        return JsonResponse({"custome_status":"Error", "message":"An return reason with the same shortcut already exist!"})
    else:
        try:
            new_return_reason = ReturnReason()
            new_return_reason.shortcut = shortcut
            new_return_reason.details = details
            new_return_reason.created_by = request.user
            new_return_reason.save()
            return JsonResponse({"custome_status":"", "message":"Return reason added succesefully!"})

        except Exception as e:
            return JsonResponse({"custome_status":"Error", "message": str(e)})



@login_required
@role_validator(['Supervisor'])
def add_batch_adjustment_reason(request):
    shortcut = request.GET.get('shortcut')
    details = request.GET.get('details')

    already_exist = BatchAdjustmentReason.objects.filter(shortcut__iexact=shortcut)
    if already_exist:
        return JsonResponse({"custome_status":"Error", "message":"An adjustment reason with the same shortcut already exist!"})
    else:
        try:
            new_batch_adjustment_reason = BatchAdjustmentReason()
            new_batch_adjustment_reason.shortcut = shortcut
            new_batch_adjustment_reason.details = details
            new_batch_adjustment_reason.created_by = request.user
            new_batch_adjustment_reason.save()
            return JsonResponse({"custome_status":"", "message":"Batch adjustment reason added succesefully!"})

        except Exception as e:
            return JsonResponse({"custome_status":"Error", "message": str(e)})


@login_required
@role_validator(['Supervisor'])
def create_return_out(request):
    batch_id = int(request.GET.get('batch_id'))
    date_returned = request.GET.get('date_returned')
    total_units_returned = int(request.GET.get('total_units_returned'))
    refund_amount = float(request.GET.get('refund_amount'))
    return_reason = int(request.GET.get('return_reason'))
    notes = request.GET.get('notes')

    batch = Batch.objects.get(id=batch_id)

    if total_units_returned > batch.total_units_available:
        return JsonResponse({"custome_status":"Error", "message":"Error! There number of units to be returned exicedes the available units!"})
    else:
        new_return_out = ReturnOut()
        new_return_out.batch = batch
        new_return_out.reason = ReturnReason.objects.get(id=return_reason)
        new_return_out.notes = notes
        new_return_out.refund_amount = refund_amount
        new_return_out.total_units = total_units_returned
        new_return_out.created_by = request.user
        new_return_out.date = date_returned
        new_return_out.save()

        batch.total_units = batch.total_units - new_return_out.total_units
        batch.save()

    return JsonResponse({"custome_status":"", "message":"Stock returned succesefully!"})


@login_required
@role_validator(['Supervisor'])
def create_batch_adjustment(request):
    batch_id = request.GET.get('batch_id')
    batch = Batch.objects.get(id=int(batch_id))

    reason_id = request.GET.get('reason')
    reason = BatchAdjustmentReason.objects.get(id=int(reason_id))
    action = request.GET.get('action')
    total_units_affected = request.GET.get('total_units_affected')
    date = request.GET.get('date')

    batch_adjustment = BatchAdjustment()
    batch_adjustment.batch = batch
    batch_adjustment.action = action
    batch_adjustment.reason = reason
    batch_adjustment.total_units = float(total_units_affected)
    batch_adjustment.date = date
    batch_adjustment.created_by = request.user
    batch_adjustment.save()

    if action == "Subtract":
        batch.total_units = float(batch.total_units) - float(total_units_affected)
        if batch.total_units < 0:
            batch_adjustment.delete()
            return JsonResponse({"custome_status":"Error", "message":f"Error! You can not subtract more than the available units. (Only {float(batch.total_units) -float(total_units_affected)} units available!)"})
    else:
        batch.total_units = float(batch.total_units) + float(total_units_affected)

    batch.save()
    content = f"Batch adjustment, { total_units_affected } {action}ed, new total {batch.total_units}, {reason.details}, Batch id: {batch_id} ( [{ batch.stock.product.product_code }] { batch.stock.product.title } { batch.stock.product.details })"
    log_activity(content, request.user)

    return JsonResponse({"custome_status":"", "message":"Batch adjusted succesefully!"})


@login_required
@role_validator(['Supervisor'])
def add_product(request):
    title = request.GET.get('title')
    hs_code = request.GET.get('hs_code')
    product_code = request.GET.get('product_code')
    details = request.GET.get('details')
    vat_code = request.GET.get('vat_code')
    category = request.GET.get('category')
    department = request.GET.get('department')
    status = request.GET.get('status')

    already_exist = Product.objects.filter(title=title, details=details)
    if already_exist:
        return JsonResponse({"custome_status":"Error", "message":"Error! Product with the exact title and details alread exist in your system"})
    else:
        new_product = Product()
        new_product.title = title
        new_product.product_code = product_code
        new_product.zimra_hs_code = hs_code
        new_product.details = details
        new_product.vat_code = VATCode.objects.get(id=int(vat_code))
        new_product.created_by = request.user
        if status == "False":
            new_product.status = False
        try:
            new_product.department = Department.objects.get(id=int(department))
        except:
            pass

        try:
            new_product.category = Category.objects.get(id=int(category))
        except:
            pass

        if hs_code != "" and is_correct_hs_code_format(hs_code) == False:
            return JsonResponse({"custome_status":"Error", "message":"You have entered an Invalid HS Code formart. If you leave it blank and it will use the VAT Code default"})

        new_product.save()

        new_stock = Stock()
        new_stock.product = new_product

        new_stock.save()
    return JsonResponse({"custome_status":"", "message":"New product served succesefully!"})



#   details

@login_required
def get_notification_details(request):
    notification_id = request.GET.get('notification_id')
    notification = Notification.objects.get(id=int(notification_id))
    notification.status = "Viewed"
    notification.save()

    header = notification.header
    notification_type = notification.notification_type
    detail = notification.detail
    created_at = notification.created_at.strftime("%a, %d %b %Y")

    details = {
        'notification_type': notification_type,
        'notification_header': header,
        'notification_date': created_at,
        'notification_detail': detail,
    }

    return JsonResponse({"details":details})



@login_required
@role_validator(['Supervisor'])
def delete_temporary_invoice_item(request):
    temporary_invoice_item_id = request.GET.get('temporary_invoice_item_id')
    # try:
    temporary_invoice_item = TemporaryInvoiceItem.objects.get(id=int(temporary_invoice_item_id))
    temporary_invoice_item.delete()
    return JsonResponse({"custome_status":"", "message":"Line deleted succesefully"})

    # except Exeption as e:
    #     return JsonResponse({"custome_status":"Error", "message":e})



@login_required
@role_validator(['Supervisor'])
def load_temporary_invoice_preview_data(request):
    temporary_invoice_available = "False"
    temporary_invoice_items_available = "False"
    try:
        discount = ReceiptPaymentEssential.objects.filter(user=request.user)[0].discount
    except:
        discount = 0

    from_company_name = ""
    from_address = ""
    from_tel = ""
    from_email = ""

    to_company_name = "" 
    to_address = "" 
    to_tel = "" 
    to_email = "" 

    try:
        configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
        to_company_name = configuration.company_name 
        to_address = configuration.address 
        to_tel = configuration.tel 
        to_email = configuration.email 
    except Exception as e:
        return JsonResponse({"custome_status":"Error", "message":"There is an error with your system configurations. Go to configurations and make sure at least one of them is active"})



    invoice_number = ""
    date_received = ""

    total_cost = 0
    subtotal = 0
    VAT = 0

    temporary_invoice_items_rows = []
    
    temporary_invoices = TemporaryInvoice.objects.filter(created_by=request.user)
    if temporary_invoices:
        temporary_invoice = temporary_invoices[0]

        temporary_invoice_available = "True"
        from_company_name = temporary_invoice.supplier.company_name 
        from_address = temporary_invoice.supplier.address 
        from_tel = temporary_invoice.supplier.phone_number 
        from_email = temporary_invoice.supplier.email 

        

        invoice_number = temporary_invoice.invoice_number

        
        date_received = str(temporary_invoice.date)[:10]
            
        for i in temporary_invoices:
            if temporary_invoice != i:
                i.delete()

        temporary_invoice_items = TemporaryInvoiceItem.objects.filter(invoice=temporary_invoice)
        if temporary_invoice_items:
            temporary_invoice_items_available = "True"


            row = []
            for temporary_invoice_item in temporary_invoice_items:
                row = [
                    f"{temporary_invoice_item.id}",
                    f"({temporary_invoice_item.stock.product.product_code}) {temporary_invoice_item.stock.product.title}",
                    f"{locale.format_string('%.0f',temporary_invoice_item.pack_size, grouping=True)}",
                    f"{locale.format_string('%.2f',temporary_invoice_item.buying_pack_price, grouping=True)}",
                    f"{locale.format_string('%.0f',temporary_invoice_item.total_packs, grouping=True)}",
                    f"{locale.format_string('%.2f',temporary_invoice_item.total_packs * temporary_invoice_item.buying_pack_price, grouping=True)}"
                ]

                temporary_invoice_items_rows.append(row)

                new_line_discount = float(temporary_invoice_item.discount_price)
                new_line_subtotal = float(temporary_invoice_item.buying_pack_price * temporary_invoice_item.total_packs)
                new_line_VAT = float((float(temporary_invoice_item.stock.product.vat_code.percentage)/100)*(new_line_subtotal))
                new_line_total_cost = new_line_subtotal + new_line_VAT

                subtotal = float(subtotal) + new_line_subtotal
                VAT = float(VAT) + new_line_VAT
                total_cost = float(total_cost) + new_line_VAT + new_line_subtotal
                discount = discount + new_line_discount






    temporary_invoice_details = {
        "temporary_invoice_available": temporary_invoice_available,
        "temporary_invoice_items_available": temporary_invoice_items_available,

        "from_company_name": from_company_name,
        "from_address": from_address,
        "from_tel": from_tel,
        "from_email": from_email,

        "to_company_name": to_company_name,
        "to_address": to_address,
        "to_tel": to_tel,
        "to_email": to_email,

        "invoice_number": invoice_number,
        "date_received": date_received,

        "total_cost": locale.format_string('%.2f',total_cost, grouping=True),
        "subtotal": locale.format_string('%.2f',subtotal, grouping=True),
        "discount": locale.format_string('%.2f',discount, grouping=True),
        "VAT": locale.format_string('%.2f',VAT, grouping=True)
    }
    return JsonResponse({"custome_status":"", "temporary_invoice_details":temporary_invoice_details, "temporary_invoice_items_rows":temporary_invoice_items_rows})



@login_required
@role_validator(['Supervisor'])
def load_current_temporary_invoice(request):
    current_temporary_invoices = TemporaryInvoice.objects.filter(created_by=request.user)
    if current_temporary_invoices:
        current_temporary_invoice = current_temporary_invoices[0]
        available = "True"

        supplier_text = current_temporary_invoice.supplier.company_name
        supplier_id = current_temporary_invoice.supplier.id
        invoice_number = current_temporary_invoice.invoice_number
        date_received = str(current_temporary_invoice.date)[:10]
        invoice_discount = current_temporary_invoice.discount

        for i in current_temporary_invoices:
            if i != current_temporary_invoice:
                i.delete()

    else:
        available = "False"

        today = datetime.strptime(str(datetime.today())[:10],"%Y-%m-%d").date()
        date_received = today
        supplier_text = ""
        supplier_id = ""
        invoice_number = ""
        invoice_discount = ""



    current_temporary_invoice_details = {
        "available": available,
        "supplier_text": supplier_text,
        "supplier_id": supplier_id,
        "invoice_number": invoice_number,
        "date_received": date_received,
        "invoice_discount": invoice_discount
    }

    return JsonResponse({"custome_status":"", "current_temporary_invoice_details":current_temporary_invoice_details})




#   listing
@login_required
def request_notifications(request):
    unread_notifications = Notification.objects.filter(status="New").count()
    return JsonResponse({'unread_notifications':unread_notifications})


@login_required
def ajax_notifications_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        notifications = Notification.objects.filter(deleted=False).order_by('-created_at')


    if request_type == "FORM-FILTER":
        # form filterr here
        notifications = Notification.objects.filter(deleted=False).order_by('-created_at')

    
    #------------------------------------------------------------------------------ 
    data_queryset = notifications
    paginator = Paginator(data_queryset, pagination_slice_leangth)  # Load 20 items per page
    # print(paginator)
    page = request.GET.get('page')
    # page = 1
    # print(page)

    try:
        data_page = paginator.page(page)
    except PageNotAnInteger:
        data_page = paginator.page(1)
    except EmptyPage:
        data_page = paginator.page(paginator.num_pages)

    #------------------------------------------------------------------------------

    rows = ""
    for notification in data_page:
        txt = str(notification.header + " " + notification.detail)[:100]
        if notification.status == "New":
            heighlight = f"""
                <td><a href="" title="Details" data-object-id="{ notification.id }" data-toggle="modal" data-target="#viewNotificationModal" id="return-out-details-modal-button"><b>{ txt }</b></a></td>
            """
        else:
            heighlight = f"""
                <td><a href="" title="Details" data-object-id="{ notification.id }" data-toggle="modal" data-target="#viewNotificationModal" id="return-out-details-modal-button">{ txt }</a></td>
            """

        if notification.notification_type == "expiring":
            type_lable = f"""
                <td> <span style="background: orange; padding: 5px; color: white; border-radius: 15px;">Expiring</span></td>
            """
        elif notification.notification_type == "expired":
            type_lable = f"""
                <td> <span style="background: red; padding: 5px; color: white; border-radius: 15px;">Expired</span></td>
            """
        else:
            type_lable = f"""
                <td> <span style="background: skyblue; padding: 5px; color: white; border-radius: 15px;">Reorder</span></td>
            """


        row = f"""
            <tr>
                <td>{ notification.id }</td>
                <td style="width: 15%; background: ">{ str(notification.created_at.strftime("%a, %d %b %Y")) }</td>
                { type_lable }
                { heighlight }
                <td> <button title="Delete" style="cursor: default" class="btn btn-danger notika-btn-danger waves-effect" onclick="deleteNotification({ notification.id })">🗑️</button></td>
            </tr>
        """
        rows += row

    table_body = f"""
        <tbody class="" style="height:200px">
            {rows}
    """

   
    table =  table_body 


    table_summery = f" {notifications.count()} out of {Notification.objects.all().count()} notifications."
    # print(f"DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD: {str(data_page)}")
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})


@login_required
@role_validator(['Data Analyst','Supervisor'])
def ajax_batch_adjustment_reasons_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        batch_adjustment_reasons = BatchAdjustmentReason.objects.filter(deleted=False).order_by('shortcut')


    if request_type == "FORM-FILTER":
        # form filterr here
        batch_adjustment_reasons = BatchAdjustmentReason.objects.filter(deleted=False).order_by('shortcut')

    
    #------------------------------------------------------------------------------ 
    data_queryset = batch_adjustment_reasons
    paginator = Paginator(data_queryset, pagination_slice_leangth)  # Load 20 items per page
    # print(paginator)
    page = request.GET.get('page')
    # page = 1
    # print(page)

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
                <th>Shortcut</th>
                <th>Details</th>
                <th>Created by</th>
                <th>Date</th>
                <th>Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for batch_adjustment_reason in data_page:
        row = f"""
            <tr>
                <td><a href="./batch/{batch_adjustment_reason.shortcut}">{ batch_adjustment_reason.shortcut }</a></td>
                <td>{ batch_adjustment_reason.details } </td>
                <td>{ batch_adjustment_reason.created_by.first_name.title() } </td>
                <td>{ str(batch_adjustment_reason.created_at)[:10] }</td>
                <td><a href="" title="Delete" class="btn btn-primary" type="button" onclick="deleteBatchAdjustmentReason({ batch_adjustment_reason.id })"><i class="notika-icon notika-trash"></a></td>
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


    table_summery = f" {batch_adjustment_reasons.count()} out of {BatchAdjustmentReason.objects.all().count()} batch adjustment reasons."
    # print(f"DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD: {str(data_page)}")
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_return_reasons_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        return_reasons = ReturnReason.objects.filter(deleted=False).order_by("shortcut")


    if request_type == "FORM-FILTER":
        # form filterr here
        return_reasons = ReturnReason.objects.filter(deleted=False).order_by("shortcut")

    
    #------------------------------------------------------------------------------ 
    data_queryset = return_reasons
    paginator = Paginator(data_queryset, pagination_slice_leangth)  # Load 20 items per page
    # print(paginator)
    page = request.GET.get('page')
    # page = 1
    # print(page)

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
                <th>Shortcut</th>
                <th>Details</th>
                <th>Created by</th>
                <th>Date</th>
                <th>Last Update</th>
                <th>Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for return_reason in data_page:
        row = f"""
            <tr>
                <td><a href="./batch/{return_reason.shortcut}">{ return_reason.shortcut }</a></td>
                <td>{ return_reason.details } </td>
                <td>{ return_reason.created_by.first_name.title() } </td>
                <td>{ str(return_reason.created_at)[:10] }</td>
                <td>{ str(return_reason.updated_at)[:10] } </td>
                <td><a href="" title="Delete" class="btn btn-primary" type="button" onclick="deleteReturnReason({ return_reason.id })"><i class="notika-icon notika-trash"></a></td>
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
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer


    table_summery = f" {return_reasons.count()} out of {ReturnReason.objects.all().count()} return reasons."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_credit_note_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')


    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        credit_notes = CreditNote.objects.all().order_by('-created_at')

    if request_type == "FORM-FILTER":
        credit_notes = CreditNote.objects.filter(deleted=False).order_by("-created_at")

        credit_note_number = request.GET.get('credit_note_number')
        receipt_number = request.GET.get('receipt_number')
        product_code = request.GET.get('product_code')
        status = request.GET.get('status')
        from_filter = request.GET.get('from')
        to_filter = request.GET.get('to')

        if credit_note_number != "":
            credit_notes = credit_notes.filter(id__contains=credit_note_number)
        if receipt_number != "":
            credit_notes = credit_notes.filter(sale_transaction__recipt_number__contains=receipt_number)
        # if status != "all" and status != "ALL":
        #     credit_notes = credit_notes.filter(status=status)
        if from_filter != "":
            credit_notes = credit_notes.filter(date__gte=from_filter)
        if to_filter != "":
            credit_notes = credit_notes.filter(date__lte=to_filter)

    
    #------------------------------------------------------------------------------ 
    data_queryset = credit_notes
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
                <th>CREDIT_NOTE</th>
                <th>Receipt #</th>
                <th style="text-align: right;">Units Returned</th>
                <th style="text-align: right;">Refund</th>
                <th>Dates</th>
                <th style="text-align: right;">Status</th>
                <th colspan="3">Manage</th>
            </tr>
        </thead>
    """
    #{ locale.format_string('%.0f', sale.quantity, grouping=True) }
    rows = ""
    for credit_note in data_page:
        if credit_note.status == "CHANGE":
            status = f""" <td> <span style="background: blue; padding: 5px; color: white; border-radius: 15px;">{ credit_note.status }</span> </td> """
        elif credit_note.status == "CLEARED":
            status = f""" <td> <span style="background: green; padding: 5px; color: white; border-radius: 15px;">{ credit_note.status }</span> </td> """
        elif credit_note.status == "BALANCE":
            status = f""" <td> <span style="background: red; padding: 5px; color: white; border-radius: 15px;">{ credit_note.status }</span> </td> """
        else:
            status = f""" <td>{ credit_note.status }</td> """
            
        row = f"""
            <tr>
                <td>{ credit_note.ultimate_credit_note_number}</td>
                <td>{ credit_note.sale_transaction.ultimate_recipt_number}</td>
                <td style="text-align: right;">{ locale.format_string('%.0f', credit_note.total_units, grouping=True) }</td>
                <td style="text-align: right;">
                    <small>Refund</small>- ${ locale.format_string('%.2f', credit_note.refund_amount, grouping=True) }<br>
                    <small>Paid</small>- ${ locale.format_string('%.2f', credit_note.paid_refund_value, grouping=True) }
                </td>
                <td>
                    <small>S</small>-{ str(credit_note.sale_transaction.created_at)[:10] }<br>
                    <small>R</small>-{ str(credit_note.created_at)[:10] }
                </td>
                { status }
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ credit_note.id }" type="button"  data-toggle="modal" data-target="#returnInnDetailsModal" id="return-inn-details-modal-button"><i class="notika-icon notika-menus"></a></td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ credit_note.id }" type="button"  data-toggle="modal" data-target="#returnInnUpdateModal" id="return-inn-update-modal-button"><i class="notika-icon notika-edit"></a></td>
                <td><a href="" title="Print out credit note" class="btn btn-primary" onclick="printCreditNote({ credit_note.id })" type="button"><i class="notika-icon notika-print"></a></td>
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


    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'data':data_page})





@login_required
@role_validator(['Data Analyst','Supervisor'])
def ajax_returns_out_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')


    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        if search_field == "all":
            returns_out = ReturnOut.objects.annotate(
                full_text = Concat(
                    'batch__batch_number', V(' '),'batch__invoice__supplier__company_name', V(' '), 'reason', output_field=CharField()
                    )
                ).filter(deleted=False, full_text__icontains=search_key).order_by('-created_at')#[:10]

        elif search_field == "Batch Number":
            returns_out = ReturnOut.objects.filter(batch___batch_number__icontains=search_key).order_by('-created_at')

        elif search_field == "Supplier":
            returns_out = ReturnOut.objects.filter(invoice__supplier__company_name__icontains=search_key).order_by('-created_at')

        else:
            pass



    if request_type == "FORM-FILTER":
        date_from = request.GET.get('form_filter_returns_out_date_from')
        date_to = request.GET.get('form_filter_returns_out_date_to')

        refund_amount_min = request.GET.get('form_filter_returns_out_refund_amount_min')
        refund_amount_max = request.GET.get('form_filter_returns_out_refund_amount_max')

        batch = request.GET.get('form_filter_returns_out_batch')
        reason = request.GET.get('form_filter_returns_out_reason')
        total_packs = request.GET.get('form_filter_returns_out_total_packs')
        operator = request.GET.get('form_filter_returns_out_operator')
        supplier = request.GET.get('form_filter_returns_out_supplier')
        

        returns_out = ReturnOut.objects.filter(deleted=False).order_by('-created_at')
        print(returns_out.count())
        if date_from != "":
            print("P Df")
            returns_out = returns_out.filter(created_at__gte=date_from)
        if date_to != "":
            print("P Dt")
            returns_out = returns_out.filter(created_at__lte=date_to)
        if batch != "all":
            print("P Df")
            returns_out = returns_out.filter(batch__id=int(batch))
        if reason != "":
            print("P Dt")
            returns_out = returns_out.filter(reason__icontains=reason)

        if refund_amount_min != "":
            print("P Qmn")
            returns_out = returns_out.filter(refund_amount__gte=int(refund_amount_min))
        if refund_amount_max != "":
            print("P Qmn")
            returns_out = returns_out.filter(refund_amount__lte=int(refund_amount_max))

        if supplier != "all" and supplier != "0":
            print("P Qmn")
            returns_out = returns_out.filter(supplier__supplier__id=int(supplier))
        if operator != "all" and operator != "0":
            print("P Qmn")
            returns_out = returns_out.filter(created_by__id=int(operator))
    
        

    
    #------------------------------------------------------------------------------ 
    data_queryset = returns_out
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
                <th style="text-align: left;">Invoice</th>
                <th>Product</th>
                <th style="text-align: right;">Total Units</th>
                <th style="text-align: right;">Refund Amt</th>
                <th style="text-align: right;">Refund Rvd</th>
                <th>Return date</th>
                <th>Date bought</th>
                <th>Status</th>
                <th colspan="2">Manage</th>
            </tr>
        </thead>
    """
    #{ locale.format_string('%.0f', sale.quantity, grouping=True) }
    rows = ""
    for return_out in data_page:
        if return_out.status == "CHANGE":
            status = f""" <td> <span style="background: blue; padding: 5px; color: white; border-radius: 15px;">{ return_out.status }</span> </td> """
        elif return_out.status == "CLEARED":
            status = f""" <td> <span style="background: green; padding: 5px; color: white; border-radius: 15px;">{ return_out.status }</span> </td> """
        elif return_out.status == "BALANCE":
            status = f""" <td> <span style="background: red; padding: 5px; color: white; border-radius: 15px;">{ return_out.status }</span> </td> """
        else:
            status = f""" <td>{ return_out.status }</td> """

        row = f"""
            <tr>
                <td style="text-align: left;">
                    <b>{ return_out.batch.invoice.invoice_number }</b><br>
                    <small>{ return_out.batch.invoice.supplier }</small>
                </td>
                <td>({ return_out.batch.stock.product.product_code.upper() }) <small>{ return_out.batch.stock.product.title.capitalize() }</small></td>
                <td style="text-align: right;">{ locale.format_string('%.0f', return_out.total_units, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', return_out.refund_amount, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', return_out.paid_refund_value, grouping=True) }</td>
                <td>{ str(return_out.date)[:10] }</td>
                <td>{ str(return_out.batch.created_at)[:10] }</td>
                { status }
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ return_out.id }" type="button"  data-toggle="modal" data-target="#returnOutDetailsModal" id="return-out-details-modal-button"><i class="notika-icon notika-menus"></a></td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ return_out.id }" type="button"  data-toggle="modal" data-target="#updateReturnOutModal" id="update-return-out-modal-button"><i class="notika-icon notika-edit"></a></td>
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
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer


    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'data':data_page})



@login_required
@role_validator(['Data Analyst','Supervisor'])
def ajax_stock_adjustment_reasons_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        stock_adjustments = BatchAdjustmentReason.objects.filter(deleted=False)


    if request_type == "FORM-FILTER":
        # form filterr here
        stock_adjustments = BatchAdjustmentReason.objects.filter(deleted=False)

    
    #------------------------------------------------------------------------------ 
    data_queryset = stock_adjustments
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
                <th>Shortcut</th>
                <th>Details</th>
                <th>Created by</th>
                <th>Date</th>
                <th>Last Update</th>
            </tr>
        </thead>
    """
    rows = ""
    for batch_adjustment_reason in data_page:
        row = f"""
            <tr>
                <td><a href="./batch/{batch_adjustment_reason.shortcut}">{ batch_adjustment_reason.shortcut }</a></td>
                <td>{ batch_adjustment_reason.details } </td>
                <td>{ batch_adjustment_reason.created_by.first_name.title() } </td>
                <td>{ str(batch_adjustment_reason.created_at)[:10] }</td>
                <td>{ str(batch_adjustment_reason.updated_at)[:10] } </td>
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


    table_summery = f" {batch_adjustment_reason.count()} out of {BatchAdjustmentReason.objects.all().count()} batch adjustment reasons."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})



@login_required
@role_validator(['Data Analyst','Supervisor'])
def ajax_batch_adjustments_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    action = request.GET.get('action')
    product_id = request.GET.get('product_id')
    batch_number = request.GET.get('batch_number')
    adjustment_reason = request.GET.get('adjustment_reason')
    user_account = request.GET.get('user_account')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        # live filter here
        stock_adjustments = BatchAdjustment.objects.filter(deleted=False).order_by('-created_at')


    if request_type == "FORM-FILTER":
        # form filterr here
        stock_adjustments = BatchAdjustment.objects.filter(deleted=False).order_by('-created_at')

        if date_from != "":
            stock_adjustments = stock_adjustments.filter(created_at__gte=date_from)
        if date_to != "":
            stock_adjustments = stock_adjustments.filter(created_at__lte=date_to)
        if action != "All":
            stock_adjustments = stock_adjustments.filter(action=action)
        if product_id != "":
            stock_adjustments = stock_adjustments.filter(batch__stock__product__product_code__icontains=product_id)
        if batch_number != "":
            stock_adjustments = stock_adjustments.filter(batch__batch_number__icontains=batch_number)
        if adjustment_reason != "" and adjustment_reason != "0":
            stock_adjustments = stock_adjustments.filter(reason__id=int(adjustment_reason))
        if user_account != "" and user_account != "all":
            stock_adjustments = stock_adjustments.filter(created_by__id=int(user_account))

    
    #------------------------------------------------------------------------------ 
    data_queryset = stock_adjustments
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
                <th>Batch</th>
                <th>Product</th>
                <th>Person</th>
                <th>Action</th>
                <th style="text-align: right;">Units</th>
                <th>On</th>
                <th>Reason</th>
                <th>Action</th>
            </tr>
        </thead>
    """
    rows = ""
    for batch_adjustment in data_page:
        row = f"""
            <tr>
                <td>{ batch_adjustment.batch.batch_number }</a></td>
                <td>({ batch_adjustment.batch.stock.product.product_code.upper() })  <small>{ batch_adjustment.batch.stock.product.title.capitalize()}</small> </td>
                <td>{ batch_adjustment.created_by.first_name.title() } </td>
                <td>{ batch_adjustment.action }ed </td>
                <td style="text-align: right;">{ batch_adjustment.total_units } </td>
                <td>{ str(batch_adjustment.created_at)[:10] }</td>
                <td title="{ batch_adjustment.reason.details }">{ batch_adjustment.reason.shortcut } </td>
                <td><button title="Delete" class="btn btn-primary" onclick="deleteBatchAdjustment({ batch_adjustment.id })"> <i class="notika-icon notika-trash"></i></button></td>
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
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer


    table_summery = f" {stock_adjustments.count()} out of {BatchAdjustment.objects.all().count()} stock adjustments."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})



@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_batches_live_search(request):
    activate_all_deactivated_batches(request)
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        if search_field == "all":
            batches = Batch.objects.annotate(
                full_text = Concat(
                    'batch_number', V(' '),'stock__product__title', V(' '), 'invoice__supplier__company_name', V(' '), 'manufacturer__company_name', output_field=CharField()
                    )
                ).filter(deleted=False, full_text__icontains=search_key).order_by('-created_at')#[:10]
                # ).filter(deleted=False, full_text__icontains=search_key, total_units__gt=0).order_by('created_at')#[:10]

        elif search_field == "Batch Number":
            batches = Batch.objects.filter(batch_number__icontains=search_key).order_by('created_at')

        elif search_field == "Supplier":
            batches = Batch.objects.filter(invoice_supplier__company_name__icontains=search_key).order_by('created_at')

        elif search_field == "Manufacturer":
            batches = Batch.objects.filter( manufacturer__company_name__icontains=search_key).order_by('created_at')

        elif search_field == "Invoice":
            batches = Batch.objects.filter( invoice__invoice_number__icontains=search_key).order_by('created_at')

        elif search_field == "Recipt Number":
            batches = Batch.objects.filter( recipt_number__icontains=search_key).order_by('created_at')

        else:
            pass



    if request_type == "FORM-FILTER":
        # date_from = request.GET.get('form_filter_batch_date_from')
        # date_to = request.GET.get('form_filter_batch_date_to')
        # supplier = request.GET.get('form_filter_batch_supplier')
        # manufacturer = request.GET.get('form_filter_batch_manufacturer')
        # invoice = request.GET.get('form_filter_batch_invoice')
        # VAT = request.GET.get('form_filter_batch_VAT')
        # recipt_number = request.GET.get('form_filter_batch_recipt_number')
        # status = request.GET.get('form_filter_batch_status')
        # created_by = request.GET.get('form_filter_batch_created_by')

        # total_packs_min_quantity = request.GET.get('form_filter_batch_total_packs_min_quantity')
        # total_packs_max_quantity = request.GET.get('form_filter_batch_total_packs_max_quantity')

        # pack_size_min_quantity = request.GET.get('form_filter_batch_pack_size_min_quantity')
        # pack_size_max_quantity = request.GET.get('form_filter_batch_pack_size_max_quantity')

        # total_units_min_quantity = request.GET.get('form_filter_batch_total_units_min_quantity')
        # total_units_max_quantity = request.GET.get('form_filter_batch_total_units_max_quantity')

        # buying_pack_price_min_quantity = request.GET.get('form_filter_batch_buying_pack_price_min_quantity')
        # buying_pack_price_max_quantity = request.GET.get('form_filter_batch_buying_pack_price_max_quantity')

        # expiration_date_from = request.GET.get('form_filter_batch_expiration_date_from')
        # expiration_date_to = request.GET.get('form_filter_batch_expiration_date_to')

        # pack_size_min_quantity = request.GET.get('form_filter_batch_pack_size_min_quantity')
        # pack_size_max_quantity = request.GET.get('form_filter_batch_pack_size_max_quantity')

        # last_updated_from = request.GET.get('form_filter_batch_last_updated_from')
        # last_updated_to = request.GET.get('form_filter_batch_last_updated_to')

        batch_number = request.GET.get('batch_number')
        product_code = request.GET.get('product_code')
        product_title = request.GET.get('product_title')

      



        batches = Batch.objects.all().order_by('-created_at')
        # batches = batches.filter(total_units__gt=0)
        
        if batch_number != "":
            batches = batches.filter(batch_number__icontains=batch_number)

        if product_code != "":
            batches = batches.filter(stock__product__product_code__icontains=product_code)

        if product_title != "":
            batches = batches.filter(stock__product__title__icontains=product_title)

        

    
    #------------------------------------------------------------------------------ 
    data_queryset = batches
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
                <th>Batch Number</th>
                <th>Product</th>
                <th style="text-align: right;">Remaining Units</th>
                <th style="text-align: right;">Buying Price</th>
                <th>Supplier</th>
                <th colspan="4">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for batch in data_page:
        # print(f"//////////////////////////////////////////////////////////////////////////////////////////////////\n {batch.buying_price}")
        # <td>{ locale.format_string('%.0f', prescription.total_repeats, grouping=True) }</td>
        if batch.status == True:
            s = "✅"
            title = "Deactivate"
        else:
            s = "⛔"
            title = "Activate"
        row = f"""
            <tr>
                <th>{ batch.batch_number }</th>
                <th>({ batch.stock.product.product_code.upper() }) { batch.stock.product.title.capitalize() } <br> <small>{ batch.stock.product.details }</small> </th>
                <td style="text-align: right;">{ locale.format_string('%.0f', batch.total_units, grouping=True) } / { locale.format_string('%.0f', batch.total_units_bought, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', batch.buying_pack_price, grouping=True) }</td>
                <td>{ batch.invoice.supplier }</td>
                <td><a href="" title="{ title }" class="btn btn-primary" data-object-id="{ batch.id }" type="button"  data-toggle="modal" data-target="#activateDeactivateBatchModal" id="activate-deactivate-batch-modal-button">{ s }</a></td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ batch.id }" type="button"  data-toggle="modal" data-target="#batchDetailsModal" id="batch-details-modal-button"><i class="notika-icon notika-menus"></a></td>
                <td><a href="" title="Adjust Batch" class="btn btn-primary" data-object-id="{ batch.id }" type="button"  data-toggle="modal" data-target="#adjustBatchModal" id="batch-details-modal-button"><i class="notika-icon notika-edit"></a></td>
                <td><a href="" title="Return Out" class="btn btn-primary" data-object-id="{ batch.id }" type="button"  data-toggle="modal" data-target="#returnOutBatchModal" id="return-batch-modal-button"><i class="notika-icon notika-next"></a></td>
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


    table_summery = f" {batches.count()} out of {Batch.objects.all().count()} batches."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})


@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_products_live_search(request):

    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        if search_field == "all":
            products = Product.objects.annotate(
                full_text = Concat(
                    'product_code', V(' '),'title', V(' '), 'details', V(' '), 'bar_code', V(' '), 'vat_code__percentage', 'vat_code__title', V(' '), output_field=CharField()
                    )
                ).filter(deleted=False, full_text__icontains=search_key).order_by('title')#[:10]
            

        elif search_field == "Product Code":
            products = Product.objects.filter(product_code__icontains=search_key).order_by('title')


        elif search_field == "VAT":
            products = Product.objects.filter(vat_code__percentage__icontains=search_key).order_by('title')

        else:
            pass



    if request_type == "FORM-FILTER":
        product_code = request.GET.get('product_code')
        product_title = request.GET.get('title')
        product_details = request.GET.get('details')
        product_category_id = request.GET.get('category')
        product_department_id = request.GET.get('department')


        products = Product.objects.filter(deleted=False).order_by('title')
        if product_code != "":
            products = products.filter(product_code__icontains=product_code)
        if product_title != "":
            products = products.filter(title__icontains=product_title)
        if product_details != "all":
            products = products.filter(details__icontains=product_details)
        if product_category_id != "all":
            products = products.filter(category__id=product_category_id)
        if product_department_id != "all":
            products = products.filter(category__id=product_department_id)

    
    #------------------------------------------------------------------------------ 
    data_queryset = products
    paginator = Paginator(data_queryset, pagination_slice_leangth)  # Load 20 items per page
    page = request.GET.get('page')


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
                <th>Product Code</th>
                <th>Title</th>
                <th>Details</th>
                <th>VAT</th>
                <th colspan="3">Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for product in data_page:
        department = ""
        category = ""
        if product.department:
            department = f"""<span title="Department" style="background: darkblue; padding: 3px; margin-right: 3px; font-size: 10px; color: white; border-radius: 10px;">{ product.department.title.title() } </span>"""
        if product.category:
            category = f"""<span title="Category" style="background: seagreen; padding: 3px; margin-right: 3px; font-size: 10px; color: white; border-radius: 10px;">{ product.category.title.title() } </span>"""
       
        row = f"""
            <tr>
                <th>{ product.product_code.upper() }</th>
                <td>{ product.title }<small></small></td>
                <td>
                    { product.details }<br>
                    { department } { category }
       
                </td>
                <td>{ locale.format_string('%.2f', product.vat_code.percentage, grouping=True) }%</td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ product.id }" type="button"  data-toggle="modal" data-target="#stockDetailsModal" id="payment-modal-button"><i class="notika-icon notika-menus"></a></td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ product.id }" type="button"  data-toggle="modal" data-target="#updateProductModal" id="payment-modal-button"><i class="notika-icon notika-edit"></a></td>
                <td><button title="Delete" class="btn btn-primary" onclick="deleteProduct({ product.id })"> <i class="notika-icon notika-trash"></i></button></td>
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


    table_summery = f" {products.count()} out of {Product.objects.all().count()} products."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})




@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_stock_prices_live_search(request):
    activate_all_deactivated_batches(request)
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')
    

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        if search_field == "all":
            stock = Stock.objects.annotate(
                full_text = Concat(
                    'product__title', V(' '),'product__details', output_field=CharField()
                    )
                ).filter(deleted=False, full_text__icontains=search_key).order_by('product__title')#[:10]

        elif search_field == "Stock":
            stock = Stock.objects.filter(product__title__icontains=search_key).order_by('product__title')

        else:
            pass



    if request_type == "FORM-FILTER":
        product_code = request.GET.get('product_code')
        product_title = request.GET.get('product_title')

       

        stock = Stock.objects.filter(deleted=False).order_by('product__title')
        if product_code != "":
            stock = stock.filter(product__product_code__icontains=product_code)
        if product_title != "":
            stock = stock.filter(product__title__icontains=product_title)
        
    
    #------------------------------------------------------------------------------ 
    data_queryset = stock
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
                <th>Product</th>
                <th style="text-align: center;">Total Units</th>
                <th style="text-align: right;">Average Buying Price</th>
                <th style="text-align: right;">Current Selling Price</th>
                <th style="text-align: right;">New Selling Price</th>
            </tr>
        </thead>
    """
    rows = ""
    for stock_ in data_page:
        if stock_.reorder_flag:
            quantity_cell = f"""<td style="text-align: right;"><a href="" style="color: red;">{ locale.format_string('%.0f', stock_.total_units, grouping=True) }</a></td>"""
        else:
            quantity_cell = f"""<td style="text-align: right;"><a href="" style="color: blue;">{ locale.format_string('%.0f', stock_.total_units, grouping=True) }</a></td>"""

        row = f"""
            <tr data-stock-id="{ stock_.id }">
                <td>
                    { stock_.product.title.upper() }<br>
                    <b>[{ stock_.product.product_code.upper() }]</b> <small>{ stock_.product.details }</small>
                </td>
                <td style="text-align: center;">{ locale.format_string('%.0f', stock_.total_units, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', stock_.avarage_unit_cost, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', stock_.selling_price, grouping=True) }</td>
                <td style="display: flex; justify-content: flex-end;"><input style="text-align: right; width: 60%; " class="form-control" type="number" value="{ locale.format_string('%.2f', stock_.selling_price, grouping=True) }"></td>
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

    table_summery = f" {stock.count()} out of {Stock.objects.filter(deleted=False).count()} stock."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})




@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_stock_live_search(request):
    activate_all_deactivated_batches(request)
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')
    

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        if search_field == "all":
            stock = Stock.objects.annotate(
                full_text = Concat(
                    'product__title', V(' '),'product__details', output_field=CharField()
                    )
                ).filter(deleted=False, full_text__icontains=search_key).order_by('product__title')#[:10]

        elif search_field == "Stock":
            stock = Stock.objects.filter(product__title__icontains=search_key).order_by('product__title')

        else:
            pass



    if request_type == "FORM-FILTER":
        product_code = request.GET.get('product_code')
        product_title = request.GET.get('product_title')

       

        stock = Stock.objects.filter(deleted=False).order_by('product__title')
        if product_code != "":
            stock = stock.filter(product__product_code__icontains=product_code)
        if product_title != "":
            stock = stock.filter(product__title__icontains=product_title)
        
    
    #------------------------------------------------------------------------------ 
    data_queryset = stock
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
                <th>Product Code</th>
                <th>Title</th>
                <th style="text-align: right;">Stock Value</th>
                <th style="text-align: right;">Quantity</th>
                <th style="text-align: right;">Rordr Qnty</th>
                <th style="text-align:right;">AVG U_Cost</th>
                <th style="text-align: right;">Selling Price</th>
                <th>Active</th>
                <th colspan='2'>Manage</th>
            </tr>
        </thead>
    """
    rows = ""
    for stock_ in data_page:
        if stock_.reorder_flag:
            quantity_cell = f"""<td style="text-align: right;"><a href="" style="color: red;">{ locale.format_string('%.0f', stock_.total_units, grouping=True) }</a></td>"""
        else:
            quantity_cell = f"""<td style="text-align: right;"><a href="" style="color: blue;">{ locale.format_string('%.0f', stock_.total_units, grouping=True) }</a></td>"""

        if stock_.status:
            tbn_title, color = "Active", "green" 
        else:
            tbn_title, color = "Frozen", "red"
            
        row = f"""
            <tr>
                <th>{ stock_.product.product_code.upper() }</th>
                <td>{ stock_.product.title.capitalize() }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', stock_.total_units * stock_.selling_price, grouping=True) }</td>
                { quantity_cell }
                <td style="text-align: right;">{ locale.format_string('%.0f', stock_.reorder_quantity, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', stock_.avarage_unit_cost, grouping=True) }</td>
                <td style="text-align: right;">{ locale.format_string('%.2f', stock_.selling_price, grouping=True) }</td>
                <td style="text-align: right;">
                    <span style="background: { color }; padding: 5px; color: white; border-radius: 15px;">{ tbn_title }</span>
                </td>
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ stock_.id }" type="button"  data-toggle="modal" data-target="#adjustStockModal" id="payment-modal-button"><i class="notika-icon notika-edit"></a></td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ stock_.id }" type="button"  data-toggle="modal" data-target="#stockDetailsModal" id="payment-modal-button"><i class="notika-icon notika-menus"></a></td>
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
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer

    table_summery = f" {stock.count()} out of {Stock.objects.filter(deleted=False).count()} stock."
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})


@login_required
@role_validator(['Data Analyst','Supervisor'])
def ajax_invoices_live_search(request):
    search_key = request.GET.get('search_key')
    search_field = request.GET.get('search_field')

    # defines the type of request: live search, form filter, initial load, etc
    request_type = request.GET.get('request_type')

    # this is for LIVE-SEARCH only // but its working fine for INITIAL-LOAD
    if request_type == "LIVE-SEARCH" or request_type == "INITIAL-LOAD":
        if search_field == "all":
            invoices = Invoice.objects.annotate(
                full_text = Concat(
                    'invoice_number', V(' '),'supplier__company_name', output_field=CharField()
                    )
                ).filter(deleted=False, full_text__icontains=search_key).order_by('-created_at')#[:10]
            # print(f"))))))))))))))))))))))))\n {invoices}")

        elif search_field == "Invoice Number":
            invoices = Invoice.objects.filter(invoice_number__icontains=search_key).order_by('-created_at')

        elif search_field == "Supplier":
            invoices = Invoice.objects.filter(supplier__company_name__icontains=search_key).order_by('-created_at')

        else:
            pass



    if request_type == "FORM-FILTER":
        
        date_to = request.GET.get('date_to')
        date_from = request.GET.get('date_from')
        invoice_number = request.GET.get('invoice_number')
        supplier = request.GET.get('supplier')

        invoices = Invoice.objects.filter(deleted=False).order_by('created_at')
        
        if date_from != "":
            invoices = invoices.filter(created_at__date__gte=date_from)
        if date_to != "":
            invoices = invoices.filter(created_at__date__lte=date_to)
        if invoice_number != "":
            invoices = invoices.filter(invoice_number__icontains=invoice_number)
        if supplier != "":
            invoices = invoices.filter(supplier__company_name__icontains=supplier)
    
    
    #------------------------------------------------------------------------------ 
    try:
        data_queryset = invoices
    except:
        data_queryset = Invoice.objects.filter(deleted=False)
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
                <th>Invoice</th>
                <th>Supplier</th>
                <th style="text-align:right;">Subtotal</th>
                <th style="text-align:right;">Discount</th>
                <th style="text-align:right;">Total Cost</th>
                <th style="text-align:right;">Paid</th>
                <th style="text-align:right;">Balance</th>
                <th>Date</th>
                <th>Status</th>
                <th colspan="2" >Manage</th>
            </tr>
        </thead>
    """
    # { locale.format_string('%.0f', sale.quantity, grouping=True) }
    rows = ""

    for invoice in data_page:
        if invoice.status == "CHANGE":
            status = f""" <td> <span style="background: blue; padding: 5px; color: white; border-radius: 15px;">{ invoice.status } </span> </td> """
        elif invoice.status == "CLEARED":
            status = f""" <td> <span style="background: green; padding: 5px; color: white; border-radius: 15px;">{ invoice.status } </span> </td> """
        elif invoice.status == "BALANCE":
            status = f""" <td> <span style="background: red; padding: 5px; color: white; border-radius: 15px;">{ invoice.status } </span> </td> """
        else:
            status = f""" <td>{ invoice.status }</td> """

        row = f"""
            <tr>
                <th>{ invoice.invoice_number }</th>
                <td>{ invoice.supplier }</td>
                <td style="text-align:right;">{ locale.format_string('%.2f', invoice.subtotal, grouping=True) }</td>
                <td style="text-align:right;">{ locale.format_string('%.2f', invoice.total_discount, grouping=True) }</td>
                <td style="text-align:right;">{ locale.format_string('%.2f', invoice.total_cost, grouping=True) }</td>
                <td style="text-align:right;">{ locale.format_string('%.2f', invoice.total_paid, grouping=True) }</td>
                <td style="text-align:right;">{ locale.format_string('%.2f', invoice.balance, grouping=True) }</td>
                <td>{ str(invoice.date)[:10] }</td>
                { status }
                <td><a href="" title="Update" class="btn btn-primary" data-object-id="{ invoice.id }" type="button"  data-toggle="modal" data-target="#updateInvoiceModal" id="update-invoice-modal-button"><i class="notika-icon notika-edit"></a></td>
                <td><a href="" title="Details" class="btn btn-primary" data-object-id="{ invoice.id }" type="button"  data-toggle="modal" data-target="#invoiceDetailsModal" id="invoice-details-modal-button"><i class="notika-icon notika-menus"></a></td>
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
            </tr>
        </tbody>
    """
    table = table_header + table_body + table_footer


    table_summery = f" {data_queryset.count()} out of {Invoice.objects.filter(deleted=False).count()} invoices."
    print(f"DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD: {str(data_page)}")
    data_page = str(data_page).replace("<","").replace(">","")

    return JsonResponse({'table':table, 'table_summery':table_summery, 'data':data_page})


#   options


@login_required
def load_live_invoice_options(request):
    # search key
    try:
        search_query = request.GET.get('search')
        invoices = Invoice.objects.filter(deleted=False, invoice_number__icontains=search_query)[:10]
    except:
        invoices = Invoice.objects.filter(deleted=False)[:10]
    

    invoice_options = [
        f"<option value='{ invoice.id }'>{ str(invoice.date)[:10]}] { invoice.invoice_number.upper() } - { invoice.supplier.company_name.title()} </option>" for invoice in invoices
    ]

    title_option = [
        f"<option value='0' selected>Select Invoice</option>"
    ]

    invoice_options = title_option + invoice_options

    return JsonResponse({'options':invoice_options})



@login_required
def load_live_category_options(request):
    # search key
    try:
        search_query = request.GET.get('search')
        categorys = Category.objects.filter(deleted=False, status=True, title__icontains=search_query)[:6]
    except:
        categorys = Category.objects.filter(deleted=False, status=True)[:10]
    

    category_options = [
        f"<option value='{ category.id }'>{ category.title.title() } </option>" for category in categorys
    ]

    title_option = [
        f"<option value='0' selected>Select Category</option>"
    ]

    category_options = title_option + category_options

    return JsonResponse({'options':category_options})



@login_required
def load_live_department_options(request):
    # search key
    try:
        search_query = request.GET.get('search')
        departments = Department.objects.filter(deleted=False, status=True, title__icontains=search_query)[:6]
    except:
        departments = Department.objects.filter(deleted=False, status=True)[:10]
    

    department_options = [
        f"<option value='{ department.id }'>{ department.title.title() } </option>" for department in departments
    ]

    title_option = [
        f"<option value='0' selected>Select Department</option>"
    ]

    department_options = title_option + department_options

    return JsonResponse({'options':department_options})



@login_required
def load_live_return_reason_options(request):
    # search key
    try:
        search_query = request.GET.get('search')
        return_reasons = ReturnReason.objects.filter(deleted=False, status=True, shortcut__icontains=search_query)[:10]
    except:
        return_reasons = ReturnReason.objects.filter(deleted=False, status=True)[:10]
    

    return_reason_options = [
        f"<option value='{ return_reason.id }'>{ return_reason.shortcut.title() } </option>" for return_reason in return_reasons
    ]

    title_option = [
        f"<option value='0' selected>Select Return Reason</option>"
    ]

    return_reason_options = title_option + return_reason_options

    return JsonResponse({'options':return_reason_options})



@login_required
def load_live_batch_adjustment_reason_options(request):
    # search key
    try:
        search_query = request.GET.get('search')
        batch_adjustment_reasons = BatchAdjustmentReason.objects.filter(deleted=False, status=True, shortcut__icontains=search_query)[:10]
    except:
        batch_adjustment_reasons = BatchAdjustmentReason.objects.filter(deleted=False, status=True)[:10]
    

    batch_adjustment_reason_options = [
        f"<option value='{ batch_adjustment_reason.id }'>{ batch_adjustment_reason.shortcut } </option>" for batch_adjustment_reason in batch_adjustment_reasons
    ]

    title_option = [
        f"<option value='0' selected>Select Adjustment Reason</option>"
    ]

    batch_adjustment_reason_options = title_option + batch_adjustment_reason_options

    return JsonResponse({'options':batch_adjustment_reason_options})



@login_required
def load_live_product_options(request):
    search_query = request.GET.get('search',"")

    products = Product.objects.filter(
        Q(title__icontains=search_query) |
        Q(product_code__icontains=search_query) |
        Q(details__icontains=search_query),
        deleted=False,
        status=True
    )[:6]       
    product_options = [
        f"<option value='{product.id}'>({ product.product_code }){ product.title } { product.details } </option>" for product in products
    ]

    return JsonResponse({'options': product_options})


@login_required
def load_live_stock_options(request):
    # search key
    # try:
    search_query = request.GET.get('search',"")

    # stock
    # stocks = Stock.objects.filter(Q(product__title__icontains=search_query) | Q(product__product_code__icontains=search_query) | Q(product__details__icontains=search_query, deleted=False, status=True))[:6]
    stocks = Stock.objects.filter(
        Q(product__title__icontains=search_query) |
        Q(product__product_code__icontains=search_query) |
        Q(product__details__icontains=search_query),
        deleted=False,
        status=True
    )[:6]       
    stock_options = [
        f"<option value='{stock.id}'>({ stock.product.product_code }){ stock.product.title } { stock.product.details } </option>" for stock in stocks
    ]
    # except:
    #     stocks = Stock.objects.filter(status=True, deleted=False)[:5]#Q(product__title__icontains=search_query) | Q(product__product_code__icontains=search_query) | Q(product__details__icontains=search_query, deleted=False, status=True)[:10]
    #             #)
    #     stock_options = [
    #         f"<option value='{stock.id}'>({ stock.product.product_code }){ stock.product.title } { stock.product.details } </option>" for stock in stocks
    #     ]


    return JsonResponse({'options': stock_options})


@login_required
def load_stock_options(request):
    stocks = Stock.objects.filter(deleted=False, status=True)#.exclude(product__category__disp='Prescription Drug')[:100]
    stock_options = [
        f"<option value='{stock.id}'>{ stock.product.title } { stock.product.title } { stock.product.details } </option>" for stock in stocks
    ]

    
    return JsonResponse({'options':stock_options})

# ------------------------------------------------------------------------
# //AJAX
# ------------------------------------------------------------------------


# ------------------------------------------------------------------------
# NONE SERIALISED URLS
# ------------------------------------------------------------------------

# #   delete
@login_required
@role_validator(['Supervisor'])
@transaction.atomic
def delete_product(request):
    try:
        product_id = request.GET.get('product_id')
        force = request.GET.get('force', 'false').lower() == 'true'
        
        if not product_id:
            return JsonResponse({'type': "error", 'title': "Error", 'message': "Product ID required"}, status=400)
        
        product = Product.objects.get(id=int(product_id))
        stocks = Stock.objects.filter(product=product)
        
        if not force:
            # Check for dependencies
            for stock in stocks:
                if (Batch.objects.filter(stock=stock).exists() or
                    InvoiceItem.objects.filter(stock=stock).exists() or
                    TemporaryInvoiceItem.objects.filter(stock=stock).exists() or
                    ReturnInn.objects.filter(stock=stock).exists() or
                    Compatibility.objects.filter(car_part=stock).exists() or
                    Sale.objects.filter(stock=stock).exists() or
                    CartItem.objects.filter(stock=stock).exists() or
                    QuotationItem.objects.filter(stock=stock).exists()):
                    
                    # Count total dependencies
                    total_deps = 0
                    for s in stocks:
                        total_deps += Batch.objects.filter(stock=s).count()
                        total_deps += InvoiceItem.objects.filter(stock=s).count()
                        total_deps += TemporaryInvoiceItem.objects.filter(stock=s).count()
                        total_deps += ReturnInn.objects.filter(stock=s).count()
                        total_deps += Compatibility.objects.filter(car_part=s).count()
                        total_deps += Sale.objects.filter(stock=s).count()
                        total_deps += CartItem.objects.filter(stock=s).count()
                        total_deps += QuotationItem.objects.filter(stock=s).count()
                    
                    return JsonResponse({
                        'type': "warning",
                        'title': "Cannot Delete",
                        'message': f"This product has {total_deps} dependent record(s). Use force delete to remove everything.",
                        'has_dependencies': True,
                        'product_id': product_id
                    })
        
        # Delete dependencies if force is True
        if force:
            for stock in stocks:
                Batch.objects.filter(stock=stock).delete()
                InvoiceItem.objects.filter(stock=stock).delete()
                TemporaryInvoiceItem.objects.filter(stock=stock).delete()
                ReturnInn.objects.filter(stock=stock).delete()
                Compatibility.objects.filter(car_part=stock).delete()
                Sale.objects.filter(stock=stock).delete()
                CartItem.objects.filter(stock=stock).delete()
                QuotationItem.objects.filter(stock=stock).delete()
        
        # Delete stocks and product
        stocks.delete()
        product.delete()
        
        return JsonResponse({
            'type': "success",
            'title': "Deleted", 
            'message': "Product deleted successfully!" if not force else "Product and all related records deleted successfully!"
        })
        
    except Product.DoesNotExist:
        return JsonResponse({'type': "error", 'title': "Error", 'message': f"Product ID '{product_id}' not found"}, status=404)
    except Exception as e:
        return JsonResponse({'type': "error", 'title': "Error", 'message': str(e)}, status=500)

@login_required
@role_validator(['Supervisor'])
def delete_batch_adjustment(request):
    try:
        batch_adjustment_id = request.GET.get('batch_adjustment_id')
        batch_adjustment = BatchAdjustment.objects.get(id=int(batch_adjustment_id))
        batch_adjustment.delete()
        return JsonResponse({'type':"success",'title':"Deleted", 'message':"Batch adjustment deleted succesefully!"})
    except Exception as e:
        if str(e) == "FOREIGN KEY constraint failed":
            return JsonResponse({'type':"error",'title':"Not Deleted", 'message':f"You can not delete this batch adjustment. A number of records are depending on it!"})

        else:
            return JsonResponse({'type':"error",'title':"Error", 'message':f"{e}"})


@login_required
@role_validator(['Supervisor'])
def delete_return_reason(request):
    try:
        return_reason_id = request.GET.get('return_reason_id')
        return_reason = ReturnReason.objects.get(id=int(return_reason_id))
        return_reason.delete()
        return JsonResponse({'custome_status':"", 'message':"Return reason deleted succesefully!"})
    except Exception as e:
        if str(e) == "FOREIGN KEY constraint failed":
            return JsonResponse({'custome_status':"Error", 'message':f"You can not delete this return reason. A number of records are depending on it!"})

        else:
            return JsonResponse({'custome_status':"Error", 'message':f"{e}"})




@login_required
@role_validator(['Supervisor'])
def delete_batch_adjustment_reason(request):
    try:
        batch_adjustment_reason_id = request.GET.get('batch_adjustment_reason_id')
        batch_adjustment_reason = BatchAdjustmentReason.objects.get(id=int(batch_adjustment_reason_id))
        batch_adjustment_reason.delete()
        return JsonResponse({'custome_status':"", 'message':"Batch adjustment reason deleted succesefully!"})
    except Exception as e:
        if str(e) == "FOREIGN KEY constraint failed":
            return JsonResponse({'custome_status':"Error", 'message':f"You can not delete this batch adjustment reason. A number of records are depending on it!"})

        else:
            return JsonResponse({'custome_status':"Error", 'message':f"{e}"})





@login_required
@role_validator(['Data Analyst','Supervisor'])
def delete_return_out_refund_money_portion(request):
    try:
        return_out_refund_money_portion_id = request.GET.get('return_out_refund_money_portion_id')
        # money_portion = RefundReturnOutMoneyPortion.objects.get(id=int(return_out_refund_money_portion_id))
        money_portion = Payment.objects.get(id=int(return_out_refund_money_portion_id))
        money_portion.delete()
        return JsonResponse({'custome_status':"", 'message':"Money portion deleted succesefully!"})
    except Exception as e:
        return JsonResponse({'custome_status':"Error", 'message':f"{e}"})


@login_required
@role_validator(['Data Analyst','Supervisor'])
def delete_credit_note_refund_money_portion(request):
    try:
        credit_note_refund_money_portion_id = request.GET.get('credit_note_refund_money_portion_id')
        # money_portion = RefundReturnInnMoneyPortion.objects.get(id=int(credit_note_refund_money_portion_id))
        money_portion = Payment.objects.get(id=int(credit_note_refund_money_portion_id))
        money_portion.delete()
        return JsonResponse({'custome_status':"", 'message':"Money portion deleted succesefully!"})
    except Exception as e:
        return JsonResponse({'custome_status':"Error", 'message':f"{e}"})



@login_required
def delete_notification(request):
    try:
        notification_id = request.GET.get('notification_id')
        notification = Notification.objects.get(id=int(notification_id))
        notification.delete()
        return JsonResponse({'custome_status':"", 'message':"Notification deleted succesefully!"})
        
    except Exception as e:
        return JsonResponse({'custome_status':"Error", 'message':f"{e}"})



@login_required
def delete_current_temporary(request):
    for temporary_invoice in TemporaryInvoice.objects.filter(created_by=request.user):
        temporary_invoice.delete()

    message = "Invoice deleted"
    return JsonResponse({"message":message})


@login_required
def delete_temporary_invoice_item_(request, pk):
    temporary_invoice_item = TemporaryInvoiceItem.objects.get(id=pk)
    temporary_invoice_item.delete()
    return JsonResponse({})



@login_required
def request_current_temporary_invoice(request):
    current_temporary_invoices = TemporaryInvoice.objects.filter(created_by=request.user)
    if len(current_temporary_invoices) != 0:
        current_temporary_invoice = current_temporary_invoices[0]

        available = "True"
        supplier_text = current_temporary_invoice.supplier.company_name
        supplier_id = current_temporary_invoice.supplier.id

        invoice_number = current_temporary_invoice.invoice_number
        discount = current_temporary_invoice.discount
        # today = datetime.strptime(str(datetime.today())[:10],"%Y-%m-%d").date()
        # date = datetime.strptime(str(datetime.today())[:10],"%Y-%m-%d").date()
        date = datetime.strptime(str(current_temporary_invoice.date)[:10],"%Y-%m-%d").date()
        # date = current_temporary_invoice.date[:10]
    else:
        available = "False"
        supplier_text = " "
        supplier_id = " "

        invoice_number = " "
        discount = " "
        date = " "

    context = {
        "available":available,
        "supplier_text":supplier_text,
        "supplier_id":supplier_id,

        "invoice_number":invoice_number,
        "discount":discount,
        "date":date,
        }
    return JsonResponse(context) 



@login_required
def add_temporary_invoice(request):
    # collect
    supplier_id = request.GET.get("supplier")
    supplier = Supplier.objects.get(id=int(supplier_id))
    invoice_number = request.GET.get("invoice_number")
    discount = request.GET.get("discount")
    date = request.GET.get("date")

    # calculate: create new or update
    existing_temporary_invoices = TemporaryInvoice.objects.filter(created_by=request.user)
    if len(existing_temporary_invoices) != 0:
        current_temporary_invoice_id = existing_temporary_invoices[0].id
        for temporary_invoice in existing_temporary_invoices:
            if temporary_invoice.id != current_temporary_invoice_id:
                temporary_invoice.delete()

        up = existing_temporary_invoices[0]
        up.invoice_number = invoice_number 
        up.supplier = supplier 
        up.discount = discount 
        up.date = date

        up.save()

        message = "Temp invoice Updated succesefully"


    else:
        new_temporary_invoice = TemporaryInvoice()
        new_temporary_invoice.invoice_number = invoice_number
        new_temporary_invoice.supplier = supplier
        new_temporary_invoice.discount = discount
        new_temporary_invoice.date = date
        new_temporary_invoice.created_by = request.user

        new_temporary_invoice.save()

  
   
        message = "Temp invoice Added succesefully"
    return JsonResponse({"message":message}) 

@login_required
def add_temporary_invoice_to_stock(request):
    #find all temporary invoces for the user
    temporary_invoices = TemporaryInvoice.objects.all()
    try:
        current_temporary_invoice_id = TemporaryInvoice.objects.all()[0].id
        current_temporary_invoice = TemporaryInvoice.objects.all()[0]
    except:
        message = 'You need to create an invoice first in "invoice" tab.'
        return JsonResponse({"custome_status":"Error", "message":message})
    #deleting others
    for temporary_invoice in temporary_invoices:
        if temporary_invoice.id != current_temporary_invoice_id:
            temporary_invoice.delete()


    # moving invoice items
    temporary_invoice_items = TemporaryInvoiceItem.objects.filter(invoice__id=current_temporary_invoice_id)

    if len(temporary_invoice_items) != 0:
        pass
    else:
        message = 'You can not submit an empty Invoice. Add at least one item in "Add Items" tab.'
        return JsonResponse({"custome_status":"Error", "message":message})


    #shifting temporay invoice to real invoice
    # creating invoice
    new_invoice = Invoice()

    new_invoice.invoice_number = current_temporary_invoice.invoice_number
    new_invoice.supplier = current_temporary_invoice.supplier
    new_invoice.date = current_temporary_invoice.date
    new_invoice.discount = current_temporary_invoice.discount
    new_invoice.created_by = current_temporary_invoice.created_by
    new_invoice.created_at = current_temporary_invoice.created_at
    new_invoice.updated_at = current_temporary_invoice.updated_at
    new_invoice.deleted = current_temporary_invoice.deleted

    new_invoice.save()

    

    for temporary_invoice_item in temporary_invoice_items:
        new_invoice_item = InvoiceItem()

        new_invoice_item.invoice = new_invoice
        new_invoice_item.stock = temporary_invoice_item.stock
        new_invoice_item.manufacturer = temporary_invoice_item.manufacturer
        new_invoice_item.vat_price = temporary_invoice_item.vat_price
        new_invoice_item.vat_percentage = temporary_invoice_item.vat_percentage
        new_invoice_item.discount_price = temporary_invoice_item.discount_price
        new_invoice_item.discount_percentage = temporary_invoice_item.discount_percentage
        new_invoice_item.total_packs = temporary_invoice_item.total_packs
        new_invoice_item.pack_size = temporary_invoice_item.pack_size
        new_invoice_item.buying_pack_price = temporary_invoice_item.buying_pack_price
        new_invoice_item.total_buying_pack_price = temporary_invoice_item.total_buying_pack_price
        new_invoice_item.markup = temporary_invoice_item.markup
        new_invoice_item.selling_price = temporary_invoice_item.selling_price
        new_invoice_item.expiration_date = temporary_invoice_item.expiration_date
        new_invoice_item.batch_number = temporary_invoice_item.batch_number

        new_invoice_item.save()


        new_batch = Batch()
        new_batch.batch_number = new_invoice_item.batch_number
        new_batch.stock = new_invoice_item.stock
        new_batch.manufacturer = new_invoice_item.manufacturer
        new_batch.invoice = new_invoice_item.invoice
        new_batch.total_packs = new_invoice_item.total_packs
        new_batch.pack_size = new_invoice_item.pack_size
        new_batch.total_units = new_invoice_item.pack_size * new_invoice_item.total_packs
        new_batch.buying_pack_price = new_invoice_item.buying_pack_price
        new_batch.VAT = new_invoice_item.discount_price
        new_batch.markup = new_invoice_item.markup
        new_batch.expiration_date = new_invoice_item.expiration_date
        new_batch.created_by = request.user

        new_batch.save()

        #adjusting selling price and and markup, (All the calculations have been done puting existing price in consideration)
        stock = Stock.objects.get(id=int(new_batch.stock.id))
        stock.selling_price = temporary_invoice_item.selling_price
        stock.markup = temporary_invoice_item.markup
        stock.save()


    for temporary_invoice_item in temporary_invoice_items:
        temporary_invoice_item.delete()


    for temporary_invoice in TemporaryInvoice.objects.filter(created_by=request.user):
        temporary_invoice.delete()

    # invoice_money_portions = InvoiceMoneyPortion.objects.filter(invoice=invoice)
    invoice_money_portions = Payment.objects.filter(payment_for="INVOICE", created_by=request.user, loose_status=True)
    for invoice_money_portion in invoice_money_portions:
        invoice_money_portion.payment_for_id = new_invoice.id
        invoice_money_portion.loose_status = False
        invoice_money_portion.save()         

    message = "Invoice added to stock succesefully"
    return JsonResponse({"message":message})



@login_required
def delete_temporary_invoice(request):
    temporary_invoices = TemporaryInvoice.objects.filter(created_by=request.user)
    for temporary_invoice in temporary_invoices:
        temporary_invoice.delete()

    message = "Temporary Invoice deleted succesefully"
    return JsonResponse({"message":message})


@login_required
def get_temporary_invoice_items_for_preview(request):
    try:
        temporary_invoice = TemporaryInvoice.objects.filter(created_by=request.user)[0]
    except:
        return JsonResponse({})
    temporary_invoice_items = TemporaryInvoiceItem.objects.filter(invoice=temporary_invoice)

    table_body = ""
    counter = 0
    for temporary_invoice_item in temporary_invoice_items:
        counter +=1
        table_row = f"""
        <tr>
            <th scope="col"><small>{counter}</small></th>
            <td scope="col"><div onclick="editTemporaryInvoiceItem({temporary_invoice_item.id})" class="btn btn-warning" title="Edit"><i class="ri-edit-2-line"></i></div></td>
            <td scope="col"><div onclick="deleteTemporaryInvoiceItem({temporary_invoice_item.id})" class="btn btn-danger" title="Delete"><i class="ri-delete-bin-2-line"></i></div></td>
            <th scope="col">{temporary_invoice_item.stock.product.title} <small>{temporary_invoice_item.stock.product.details}</small></th>
            <td scope="col">{temporary_invoice_item.pack_size}</td>
            <td scope="col">{temporary_invoice_item.total_packs}</td>
            <td scope="col">{temporary_invoice_item.discount_price}</td>
            
        </tr>
        """

        table_body += table_row

    return JsonResponse({"table_body":table_body})

    

@login_required
def add_temporary_invoice_item(request):
    # try collect and assign:

    stock = request.GET.get('stock_')
    stock = Stock.objects.get(id=int(stock))

    manufacturer = request.GET.get('manufacturer')
    manufacturer = Manufacturer.objects.get(id=int(manufacturer))

    selling_price_type = request.GET.get('selling_price_type')
    selling_price_number = float(request.GET.get('selling_price_number'))
    total_packs = int(request.GET.get('total_packs'))
    pack_size = int(request.GET.get('pack_size'))
    buying_pack_price = float(request.GET.get('buying_pack_price'))
    expiration_date = request.GET.get('expiration_date')
    discount_type = request.GET.get('discount_type')
    discount_number = float(request.GET.get('discount_number'))
    batch_number = request.GET.get('batch_number')
   

    #try collect and culculete
    try:
        temporary_invoice = TemporaryInvoice.objects.filter(created_by=request.user)[0]
    except:
        message = 'You need to create an invoice first in "Invoice" tab.' 
        return JsonResponse({"custome_status":"Error","message":message})
        
    vat_price = (float(stock.product.vat_code.percentage) * 0.01) * (total_packs * buying_pack_price)
    vat_percentage = float(stock.product.vat_code.percentage) * 0.01

    if discount_type == "DISCOUNT PERCENTAGE":
        discount_price = (total_packs * buying_pack_price) * (discount_number * 0.01)
        print('discount_price')
        print(discount_price)
        discount_percentage = discount_number

    elif discount_type == "DISCOUNT PRICE":
        discount_price = discount_number
        discount_percentage = (discount_number * 0.01) * (total_packs * buying_pack_price)
    else:
        message = "You can not use the selected discount type."
        return JsonResponse({'message': message})


    total_buying_pack_price = buying_pack_price #- discount_price
   


    if selling_price_type == "MARKUP PERCENTAGE":
        markup = selling_price_number
        buying_unit_cost = buying_pack_price / pack_size
        selling_price = (markup / 100) * buying_unit_cost + buying_unit_cost 
        

    elif selling_price_type == "SELLING PRICE":
        selling_price = selling_price_number
        buying_unit_cost = buying_pack_price / pack_size
        markup = (selling_price - buying_unit_cost)/(buying_unit_cost)*100
    elif selling_price_type == "EXISTING PRICE":
        try:
            markup = stock.markup
            selling_price = stock.selling_price
        except Exception as e:
            return JsonResponse({'custome_status':'Error', 'message': "Error! You do not have an existing price  for this stock yet"})
        

    else:
        message = "You can not use the selected markup type."
        return JsonResponse({'message': message})

    


    # try  save:
    temporary_invoice_item = TemporaryInvoiceItem()
    temporary_invoice_item.invoice = temporary_invoice
    temporary_invoice_item.stock = stock
    temporary_invoice_item.selling_price_type = selling_price_type
    temporary_invoice_item.selling_price_number = selling_price_number
    temporary_invoice_item.discount_type = discount_type
    temporary_invoice_item.discount_number = discount_number
    temporary_invoice_item.manufacturer = manufacturer
    temporary_invoice_item.vat_price = vat_price
    temporary_invoice_item.vat_percentage = vat_percentage
    temporary_invoice_item.discount_price = discount_price
    temporary_invoice_item.discount_percentage = discount_percentage
    temporary_invoice_item.total_packs = total_packs
    temporary_invoice_item.pack_size = pack_size
    temporary_invoice_item.buying_pack_price = buying_pack_price
    temporary_invoice_item.total_buying_pack_price = total_buying_pack_price
    temporary_invoice_item.markup = markup
    temporary_invoice_item.selling_price = selling_price
    temporary_invoice_item.expiration_date = expiration_date
    temporary_invoice_item.batch_number = batch_number

    temporary_invoice_item.save()

    message = "Invoice item added succesefully"
    return JsonResponse({'message': message})



def print_out_credit_note(request):
    OLD_PRINT = os.getenv("OLD_PRINT", "false").lower() == "true"
    if OLD_PRINT:
        return print_out_credit_note_old(request)

    else:
        return print_out_credit_note_new(request)



@login_required
def print_out_credit_note_new(request):
    try:
        print("PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP NEW")
        credit_note_id = request.GET.get('credit_note_id')
        credit_note = CreditNote.objects.get(id=credit_note_id)
        receipt_number = credit_note.sale_transaction.recipt_number

        if credit_note:

            printer = get_printer(request)

            print_this_document(request, printer, "CREDITNOTE", credit_note.id, "")
            print_this_document(request, printer, "CREDITNOTE", credit_note.id, "(COPY)")
            return JsonResponse({"title":title, "message":"Print job sent", "type":"success"})
        else:
            message = f"No credit not found with the id {credit_note_id}."
            return JsonResponse({"title":"Error", "message":message, "type":"error"})

    except Exception as e:
        return JsonResponse({"title":"Error", "message":str(e), "type":"error"})



@login_required
def print_out_credit_note_old(request):
    try:
        credit_note_id = request.GET.get('credit_note_id')
        credit_note = CreditNote.objects.get(id=credit_note_id)
        receipt_number = credit_note.sale_transaction.recipt_number

        if credit_note:
            print("available cdnt")
            fiscal_details = get_fiscal_details("CREDITNOTE", credit_note.id)
            qr_url = fiscal_details['url']
            fiscal_device_id = fiscal_details['url']
            custome_status, message = print_out_credit_note_bulk(receipt_number, credit_note.id, "", qr_url, fiscal_device_id)
            return JsonResponse({"title":title, "message":message, "type":"success"})
        else:
            message = f"No credit not found with the id {credit_note_id}."
            return JsonResponse({"title":"Error", "message":message, "type":"error"})

    except Exception as e:
        return JsonResponse({"title":"Error", "message":str(e), "type":"error"})



#   delete

def delete_notifications(request):
    notification_type = request.GET.get('notification_type')
    custome_status, message = delete_notifications_by_type(notification_type)

    return JsonResponse({'custome_status':custome_status, 'message':message})
