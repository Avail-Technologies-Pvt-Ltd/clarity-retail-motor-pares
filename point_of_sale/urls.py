from django.conf import settings
from django.conf.urls.static import static
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
    path('fiscalisation/', include('fiscalisation.urls')),

    path('print_out/', include('print_out.urls')),
]


print(f'DEBUG MODE {settings.DEBUG}')

if settings.DEBUG:
    # add debugging tool bar
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]

    # Serving media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

else:
    # Force serve media files even in production (temporary fix)
    from django.views.static import serve
    urlpatterns += [
        path('media/<path:path>/', serve, {'document_root': settings.MEDIA_ROOT}),
    ]