# fiscalisation/urls.py
from django.urls import path
from . import views

app_name = 'fiscalisation'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('settings/', views.settings, name='settings'),
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('receipts/pending/', views.pending_receipts, name='pending_receipts'),
    path('receipts/failed/', views.failed_receipts, name='failed_receipts'),
    path('receipts/bypassed/', views.bypassed_receipts, name='bypassed_receipts'),
    path('queue/', views.sync_queue, name='sync_queue'),
    path('logs/', views.sync_logs, name='sync_logs'),
    
    path('api/pause/', views.pause_fiscalisation, name='pause_fiscalisation'),
    path('api/resume/', views.resume_fiscalisation, name='resume_fiscalisation'),
    path('api/sync-now/', views.sync_now, name='sync_now'),
    path('api/test-connection/', views.test_connection, name='test_connection'),
    path('api/receipts/<int:receipt_id>/retry/', views.retry_receipt, name='retry_receipt'),
    path('api/receipts/<int:receipt_id>/void/', views.void_receipt, name='void_receipt'),
    path('api/receipts/<int:receipt_id>/detail/', views.receipt_detail_api, name='receipt_detail_api'),
]