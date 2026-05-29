# fiscalisation/urls.py
from django.urls import path
from . import views

app_name = 'fiscalisation'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # API Endpoints
    path('api/dashboard-data/', views.get_dashboard_data, name='dashboard_data'),
    path('api/open-day/', views.open_fiscal_day, name='open_day'),
    path('api/close-day/', views.close_fiscal_day, name='close_day'),
    path('api/create-test-receipt/', views.create_test_receipt, name='create_test_receipt'),
    path('api/refresh-status/', views.refresh_status, name='refresh_status'),
]