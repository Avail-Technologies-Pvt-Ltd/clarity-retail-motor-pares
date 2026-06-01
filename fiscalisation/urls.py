# fiscalisation/urls.py

from django.urls import path
from . import views

urlpatterns = [

    path("ping/", views.ping_device),

    path("config/", views.get_config),

    path("status/", views.get_status),

    path("open-day/", views.open_day),

    path("test-receipt/", views.test_receipt),

    path("close-day/", views.close_day),

]