from django.urls import path
from . import views


urlpatterns = [
    # html
    path('create_backup', views.create_backup, name='create_backup'),
    path('add_subscription_page', views.add_subscription_page, name='add_subscription_page'),
    path('system_settings', views.system_settings, name='system_settings'),
    
    # HELPER FUNCTIONS
    path('days_from_now', views.days_from_now, name='days_from_now'),
    
    # API ENDPOINTS FOR SYSTEM SETTINGS (AJAX)
    path('api/update_user_profile', views.api_update_user_profile, name='api_update_user_profile'),
    path('api/update_branch', views.api_update_branch, name='api_update_branch'),
    path('api/update_client_setting', views.api_update_client_setting, name='api_update_client_setting'),
    path('api/update_printer', views.api_update_printer, name='api_update_printer'),
    path('api/delete_printer', views.api_delete_printer, name='api_delete_printer'),  # ADD THIS LINE
    path('api/activate_subscription', views.api_activate_subscription, name='api_activate_subscription'),
    path('api/get_update_log', views.api_get_update_log, name='api_get_update_log'),
    path('api/create_branch', views.api_create_branch, name='api_create_branch'),
]