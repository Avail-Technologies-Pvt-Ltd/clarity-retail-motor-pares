from django.contrib import admin
from django.urls import path, include

from accounts import views

urlpatterns = [
    path('api/', include('accounts.urls')),


    path("admin/", admin.site.urls),
    path('', views.home, name='home'),
    path('home', views.home, name='home'),

    path('accounts/', include('accounts.urls')),
    path('enventory/', include('enventory.urls')),
    path('payments/', include('payments.urls')),
    path('reports/', include('reports.urls')),
    path('pos/', include('pos.urls')),

    path('order/', include('order.urls')),
    path('knowledge_base/', include('knowledge_base.urls')),
]
