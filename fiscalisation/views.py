# fiscalisation/views.py
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import FiscalisationSettings, FiscalReceipt, SyncQueue, SyncLog
from .services import FiscalisationService, BinaryAPIClient

logger = logging.getLogger(__name__)


@staff_member_required
def dashboard(request):
    service = FiscalisationService()
    
    context = {
        'active_tab': 'dashboard',
        'fiscalisation_active': service.is_fiscalisation_active(),
        'total_receipts': FiscalReceipt.objects.count(),
        'synced_count': service.get_synced_count(),
        'pending_count': service.get_pending_count(),
        'failed_count': service.get_failed_count(),
        'bypassed_count': service.get_bypassed_count(),
        'recent_receipts': FiscalReceipt.objects.all().order_by('-created_at')[:20],
        'queue_items': SyncQueue.objects.filter(scheduled_for__lte=timezone.now()).select_related('fiscal_receipt')[:10],
        'sync_logs': SyncLog.objects.all().order_by('-attempt_time')[:10],
    }
    return render(request, 'fiscalisation/dashboard.html', context)


@staff_member_required
def settings(request):
    if request.method == 'POST':
        settings_obj = FiscalisationSettings.get_settings()
        settings_obj.api_base_url = request.POST.get('api_base_url')
        settings_obj.device_id = request.POST.get('device_id')
        settings_obj.machine_code = request.POST.get('machine_code')
        settings_obj.api_password = request.POST.get('api_password')
        settings_obj.sync_interval_seconds = int(request.POST.get('sync_interval_seconds', 30))
        settings_obj.max_retry_count = int(request.POST.get('max_retry_count', 5))
        settings_obj.admin_email = request.POST.get('admin_email', '')
        settings_obj.admin_phone = request.POST.get('admin_phone', '')
        settings_obj.auto_resume_on_success = request.POST.get('auto_resume_on_success') == 'on'
        settings_obj.save()
        messages.success(request, 'Settings saved successfully')
        return redirect('fiscalisation:settings')
    
    service = FiscalisationService()
    settings_obj = FiscalisationSettings.get_settings()
    
    context = {
        'active_tab': 'settings',
        'fiscalisation_active': service.is_fiscalisation_active(),
        'settings': settings_obj,
        'total_receipts': FiscalReceipt.objects.count(),
        'pending_count': service.get_pending_count(),
        'failed_count': service.get_failed_count(),
    }
    return render(request, 'fiscalisation/settings.html', context)


@staff_member_required
def receipt_list(request):
    receipts_list = FiscalReceipt.objects.all().order_by('-created_at')
    
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    
    if status_filter:
        receipts_list = receipts_list.filter(status=status_filter)
    if type_filter:
        receipts_list = receipts_list.filter(receipt_type=type_filter)
    
    paginator = Paginator(receipts_list, 50)
    receipts = paginator.get_page(request.GET.get('page'))
    
    context = {
        'active_tab': 'receipts',
        'fiscalisation_active': FiscalisationService().is_fiscalisation_active(),
        'receipts': receipts,
        'status_filter': status_filter,
        'type_filter': type_filter,
    }
    return render(request, 'fiscalisation/receipt_list.html', context)


@staff_member_required
def pending_receipts(request):
    receipts = FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_PENDING).order_by('created_at')
    context = {'active_tab': 'receipts', 'receipts': receipts, 'title': 'Pending Sync'}
    return render(request, 'fiscalisation/receipt_list.html', context)


@staff_member_required
def failed_receipts(request):
    receipts = FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_FAILED).order_by('-created_at')
    context = {'active_tab': 'receipts', 'receipts': receipts, 'title': 'Failed Receipts'}
    return render(request, 'fiscalisation/receipt_list.html', context)


@staff_member_required
def bypassed_receipts(request):
    receipts = FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_BYPASSED).order_by('-created_at')
    context = {'active_tab': 'receipts', 'receipts': receipts, 'title': 'Bypassed Receipts'}
    return render(request, 'fiscalisation/receipt_list.html', context)


@staff_member_required
def sync_queue(request):
    queue_items = SyncQueue.objects.select_related('fiscal_receipt').all().order_by('-priority', 'scheduled_for')
    context = {'active_tab': 'queue', 'queue_items': queue_items}
    return render(request, 'fiscalisation/sync_queue.html', context)


@staff_member_required
def sync_logs(request):
    logs = SyncLog.objects.all().order_by('-attempt_time')[:100]
    context = {'active_tab': 'logs', 'logs': logs}
    return render(request, 'fiscalisation/sync_logs.html', context)


# API endpoints
@csrf_exempt
@staff_member_required
def pause_fiscalisation(request):
    if request.method == 'POST':
        service = FiscalisationService()
        data = json.loads(request.body) if request.body else {}
        service.pause_fiscalisation(reason=data.get('reason', 'Admin action'), user=request.user.username)
        return JsonResponse({'success': True})


@csrf_exempt
@staff_member_required
def resume_fiscalisation(request):
    if request.method == 'POST':
        service = FiscalisationService()
        service.resume_fiscalisation()
        return JsonResponse({'success': True})


@csrf_exempt
@staff_member_required
def sync_now(request):
    if request.method == 'POST':
        service = FiscalisationService()
        results = service.sync_pending_receipts()
        return JsonResponse({'success': True, 'synced': results['success'], 'failed': results['failed'], 'total': results['total']})


@csrf_exempt
@staff_member_required
def test_connection(request):
    if request.method == 'POST':
        settings_obj = FiscalisationSettings.get_settings()
        
        if not settings_obj.device_id:
            return JsonResponse({'success': False, 'error': 'Device ID not configured'})
        if not settings_obj.machine_code:
            return JsonResponse({'success': False, 'error': 'Machine Code not configured'})
        if not settings_obj.api_password:
            return JsonResponse({'success': False, 'error': 'API Password not configured'})
        
        try:
            client = BinaryAPIClient()
            result = client.get_status()
            
            if result and 'error' not in result:
                return JsonResponse({'success': True, 'message': 'Connection successful!', 'response': result})
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No response'
                return JsonResponse({'success': False, 'error': error_msg})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@staff_member_required
def retry_receipt(request, receipt_id):
    if request.method == 'POST':
        service = FiscalisationService()
        success = service.retry_failed_receipt(receipt_id)
        return JsonResponse({'success': success})


@csrf_exempt
@staff_member_required
def void_receipt(request, receipt_id):
    if request.method == 'POST':
        service = FiscalisationService()
        success = service.void_receipt(receipt_id)
        return JsonResponse({'success': success})


@staff_member_required
def receipt_detail_api(request, receipt_id):
    receipt = get_object_or_404(FiscalReceipt, id=receipt_id)
    
    html = f'''
    <div class="row">
        <div class="col-md-6">
            <table class="table table-bordered">
                <tr><th>Fiscal #</th><td>{receipt.fiscal_receipt_number or '—'}</td></tr>
                <tr><th>Global #</th><td>{receipt.fiscal_receipt_global_no or '—'}</td></tr>
                <tr><th>Internal Invoice</th><td>{receipt.internal_invoice_number}</td></tr>
                <tr><th>Type</th><td>{receipt.receipt_type}</td></tr>
                <tr><th>Total</th><td>{receipt.currency} {receipt.total_amount:.2f}</td></tr>
            </table>
        </div>
        <div class="col-md-6">
            <table class="table table-bordered">
                <tr><th>Status</th><td>{receipt.get_status_display()}</td></tr                <tr><th>Created</th><td>{receipt.created_at|date:"Y-m-d H:i:s"}</td></tr>
                <tr><th>Retry Count</th><td>{receipt.retry_count}/5</tr
            </table>
        </div>
    </div>
    '''
    
    if receipt.last_error:
        html += f'<div class="alert alert-danger">Error: {receipt.last_error}</div>'
    
    if receipt.qr_code_url:
        html += f'<div class="text-center"><a href="{receipt.qr_code_url}" target="_blank" class="btn btn-info">View QR Code</a></div>'
    
    return JsonResponse({'html': html})