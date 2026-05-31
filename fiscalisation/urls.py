# fiscalisation/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # UI — dashboard + device management
    path("dashboard/", views.dashboard, name="fiscal_dashboard"),
    path("devices/", views.device_list, name="fiscal_device_list"),
    path("devices/add/", views.device_add, name="fiscal_device_add"),
    path("devices/<int:pk>/", views.device_detail, name="fiscal_device_detail"),
    path("devices/<int:pk>/register/", views.device_register_with_zimra, name="fiscal_device_register"),
    path("devices/<int:pk>/upload-cert/", views.device_upload_cert, name="fiscal_device_upload_cert"),
    path("devices/<int:pk>/set-active/", views.device_set_active, name="fiscal_device_set_active"),
    path("devices/<int:pk>/test/", views.device_test, name="fiscal_device_test"),
    path("devices/<int:pk>/delete/", views.device_delete, name="fiscal_device_delete"),

    # Direct device endpoints
    path("ping/", views.ping_device),
    path("config/", views.get_config),
    path("status/", views.get_status),
    path("open-day/", views.open_day),
    path("test-receipt/", views.test_receipt),
    path("close-day/", views.close_day),

    # api/ aliases used by dashboard JS
    path("api/open-day/", views.open_day),
    path("api/close-day/", views.close_day),
    path("api/dashboard-data/", views.dashboard_data),
    path("api/create-test-receipt/", views.test_receipt),
    path("api/status/", views.get_status),
    path("api/ping/", views.ping_device),
    path("api/config/", views.get_config),
    path("api/reconcile/", views.reconcile),
    path("api/sync-pending/", views.sync_pending_now),
]
