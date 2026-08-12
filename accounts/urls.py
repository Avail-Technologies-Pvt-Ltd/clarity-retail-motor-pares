from django.urls import path
from .import views


urlpatterns = [
    path('new_users_list_f/', views.new_users_list_f, name='new_users_list_f'),
    
    #html pages
    path('login_page/', views.login_page, name='login_page'),
    path('users_page/', views.users_page, name='users_page'),
    path('customers_page/', views.customers_page, name='customers_page'),
    path('suppliers_page/', views.suppliers_page, name='suppliers_page'),
    path('manufacturers_page/', views.manufacturers_page, name='manufacturers_page'),
    path('client_settings_page/', views.client_settings_page, name='client_settings_page'),


    #   add
    path('add_user', views.add_user, name='add_user'),
    path('add_supplier', views.add_supplier, name='add_supplier'),
    path('add_customer', views.add_customer, name='add_customer'),
    path('add_manufacturer', views.add_manufacturer, name='add_manufacturer'),
    path('add_configuration', views.add_configuration, name='add_configuration'),
    path('add_note', views.add_note, name='add_note'),

    #   update
    path('update_user', views.update_user, name='update_user'),
    path('update_supplier', views.update_supplier, name='update_supplier'),
    path('update_customer', views.update_customer, name='update_customer'),
    path('update_manufacturer', views.update_manufacturer, name='update_manufacturer'),
    path('update_configuration', views.update_configuration, name='update_configuration'),


    #   details
    path('get_user_details', views.get_user_details, name='get_user_details'),
    path('get_supplier_details', views.get_supplier_details, name='get_supplier_details'),
    path('get_manufacturer_details', views.get_manufacturer_details, name='get_manufacturer_details'),
    path('get_customer_details', views.get_customer_details, name='get_customer_details'),
    path('get_configuration_details', views.get_configuration_details, name='get_configuration_details'),


    #   listing
    path('ajax_suppliers_live_search', views.ajax_suppliers_live_search, name='ajax_suppliers_live_search'),
    path('ajax_manufacturers_live_search', views.ajax_manufacturers_live_search, name='ajax_manufacturers_live_search'),
    path('ajax_customers_live_search', views.ajax_customers_live_search, name='ajax_customers_live_search'),
    path('ajax_users_live_search', views.ajax_users_live_search, name='ajax_users_live_search'),
    path('ajax_configurations_live_search/', views.ajax_configurations_live_search, name='ajax_configurations_live_search'),
    path('ajax_notes_live_search', views.ajax_notes_live_search, name='ajax_notes_live_search'),
    

    # ajax
    #   options
    path('load_live_users_options/', views.load_live_users_options, name='load_live_users_options'),
    path('load_live_suppliers_options/', views.load_live_suppliers_options, name='load_live_suppliers_options'),
    path('load_live_manufacturers_options/', views.load_live_manufacturers_options, name='load_live_manufacturers_options'),
    
    path('load_customer_options/', views.load_customer_options, name='load_customer_options'),
    

    # authentication
    path('login/', views.login, name='login'),
    path('user_logout/', views.user_logout, name='user_logout'),


    #   delete
    path('delete_note', views.delete_note, name='delete_note'),
    path('suppliers/', views.suppliers_list, name='suppliers'),




    # NEW SETTINGS
    path('update_company_details', views.update_company_details, name='update_company_details'),
    path('update_branch_settings', views.update_branch_settings, name='update_branch_settings'),
    path('update_invoice_settings', views.update_invoice_settings, name='update_invoice_settings'),
    path('update_display_settings', views.update_display_settings, name='update_display_settings'),






    
    
]