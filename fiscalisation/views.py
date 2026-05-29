# fiscalisation/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import datetime, date
import json
import logging

# Import your models - ADD THESE IMPORTS
from .models import FiscalReceipt, FiscalDaySummary, FiscalState, FiscalDevice
from .services import ZIMRAService

logger = logging.getLogger(__name__)

# Initialize service
try:
    zimra_service = ZIMRAService()
except Exception as e:
    logger.error(f"Failed to initialize ZIMRA service: {str(e)}")
    zimra_service = None

@staff_member_required
def dashboard(request):
    """Main dashboard page with buttons for ZIMRA operations"""
    context = {
        'title': 'Fiscalisation Dashboard',
        'current_time': datetime.now(),
    }
    return render(request, 'fiscalisation/dashboard.html', context)

@staff_member_required
def get_dashboard_data(request):
    """API endpoint to get all dashboard data for AJAX updates"""
    try:
        if not zimra_service:
            return JsonResponse({'success': False, 'error': 'ZIMRA service not initialized'})
        
        # Get device status
        device_status = zimra_service.get_device_status()
        
        # Get fiscal state
        fiscal_state = zimra_service.get_fiscal_state()
        
        # Get today's receipts
        today = date.today()
        today_receipts = FiscalReceipt.objects.filter(
            fiscal_state=fiscal_state,
            created_at__date=today
        )
        
        # Get latest receipts (last 10)
        latest_receipts = FiscalReceipt.objects.filter(
            fiscal_state=fiscal_state
        ).order_by('-created_at')[:10]
        
        # Get summary for current fiscal day
        current_day_summary = None
        if fiscal_state.is_day_open and fiscal_state.current_day_date:
            day_receipts = FiscalReceipt.objects.filter(
                fiscal_state=fiscal_state,
                created_at__date=fiscal_state.current_day_date
            )
            total_sales = day_receipts.aggregate(total=Sum('total_amount'))['total'] or 0
            current_day_summary = {
                'total_receipts': day_receipts.count(),
                'total_sales': float(total_sales),
                'first_receipt': day_receipts.first().receipt_global_no if day_receipts.exists() else None,
                'last_receipt': day_receipts.last().receipt_global_no if day_receipts.exists() else None,
            }
        
        # Get recent day summaries
        recent_days = FiscalDaySummary.objects.filter(
            fiscal_state=fiscal_state
        ).order_by('-day_date')[:5]
        
        data = {
            'device_status': {
                'is_connected': device_status.get('success', False),
                'is_day_open': device_status.get('fiscal_day_open', False),
                'current_day_no': device_status.get('current_day_no', 0),
                'next_receipt_counter': device_status.get('next_receipt_counter', 1),
                'next_global_no': device_status.get('next_global_no', 1),
                'taxpayer_name': device_status.get('taxpayer_name', 'N/A'),
                'device_serial': device_status.get('device_serial', 'N/A'),
                'certificate_valid_till': device_status.get('certificate_valid_till', 'N/A'),
            },
            'fiscal_state': {
                'day_open': fiscal_state.is_day_open,
                'day_number': fiscal_state.fiscal_day_no if not fiscal_state.is_day_open else fiscal_state.fiscal_day_no,
                'receipt_counter': fiscal_state.receipt_counter,
                'global_no': fiscal_state.receipt_global_no,
                'current_day_date': fiscal_state.current_day_date.strftime('%Y-%m-%d') if fiscal_state.current_day_date else None,
            },
            'current_day_summary': current_day_summary,
            'latest_receipts': [
                {
                    'global_no': r.receipt_global_no,
                    'invoice_no': r.invoice_no,
                    'type': r.receipt_type,
                    'total': float(r.total_amount),
                    'qr_url': r.qr_code_url,
                    'created_at': r.created_at.strftime('%H:%M:%S'),
                    'receipt_id': r.receipt_id,
                }
                for r in latest_receipts
            ],
            'recent_summaries': [
                {
                    'day_no': s.fiscal_day_no,
                    'date': s.day_date.strftime('%Y-%m-%d'),
                    'receipts': s.total_receipts,
                    'sales': float(s.total_sales),
                }
                for s in recent_days
            ],
            'today_stats': {
                'count': today_receipts.count(),
                'total': float(today_receipts.aggregate(total=Sum('total_amount'))['total'] or 0),
            }
        }
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        import traceback
        traceback.print_exc()  # This will print the full error to console
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
@require_http_methods(["POST"])
def open_fiscal_day(request):
    """Open a new fiscal day"""
    try:
        if not zimra_service:
            return JsonResponse({'success': False, 'error': 'ZIMRA service not initialized'})
            
        result = zimra_service.open_fiscal_day()
        if result.get('success'):
            messages.success(request, f"Fiscal Day {result['fiscal_day_no']} opened successfully!")
            return JsonResponse({'success': True, 'message': result['message'], 'data': result})
        else:
            messages.error(request, f"Failed to open fiscal day: {result.get('error')}")
            return JsonResponse({'success': False, 'error': result.get('error')}, status=400)
    except Exception as e:
        logger.error(f"Error opening fiscal day: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@staff_member_required
@require_http_methods(["POST"])
def close_fiscal_day(request):
    """Close the current fiscal day"""
    try:
        if not zimra_service:
            return JsonResponse({'success': False, 'error': 'ZIMRA service not initialized'})
            
        result = zimra_service.close_fiscal_day()
        if result.get('success'):
            messages.success(request, f"Fiscal Day {result['fiscal_day_no']} closed successfully!")
            return JsonResponse({'success': True, 'message': result['message'], 'data': result})
        else:
            messages.error(request, f"Failed to close fiscal day: {result.get('error')}")
            return JsonResponse({'success': False, 'error': result.get('error')}, status=400)
    except Exception as e:
        logger.error(f"Error closing fiscal day: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@staff_member_required
@require_http_methods(["POST"])
def create_test_receipt(request):
    """Create and submit a test receipt"""
    try:
        if not zimra_service:
            return JsonResponse({'success': False, 'error': 'ZIMRA service not initialized'})
            
        # Create test receipt data
        test_items = [
            {
                'name': 'Test Product A',
                'quantity': 2,
                'price': 49.99,
                'tax_percent': 15.5,
                'hs_code': '84713000'
            },
            {
                'name': 'Test Product B',
                'quantity': 1,
                'price': 29.99,
                'tax_percent': 0,
                'hs_code': '04021099'
            },
        ]
        
        receipt_data = {
            'invoice_no': f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'receipt_type': 'FISCALINVOICE',
            'currency': 'USD',
            'payment_type': 0,
            'items': test_items
        }
        
        result = zimra_service.process_receipt(receipt_data)
        
        if result.get('success'):
            messages.success(request, f"Test receipt submitted! Global #{result['receipt_global_no']}")
            return JsonResponse({'success': True, 'data': result})
        else:
            messages.error(request, f"Failed to submit test receipt: {result.get('error')}")
            return JsonResponse({'success': False, 'error': result.get('error')}, status=400)
            
    except Exception as e:
        logger.error(f"Error creating test receipt: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@staff_member_required
@require_http_methods(["POST"])
def refresh_status(request):
    """Refresh device status"""
    try:
        if not zimra_service:
            return JsonResponse({'success': False, 'error': 'ZIMRA service not initialized'})
            
        status = zimra_service.get_device_status()
        return JsonResponse({'success': True, 'data': status})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})