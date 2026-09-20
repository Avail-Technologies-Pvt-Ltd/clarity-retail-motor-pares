
from django.urls import path
from .import views


urlpatterns = [
    
    path('load_data', views.load_data, name='load_data'),
    #   html
    path('transactions_summery_page', views.transactions_summery_page, name='transactions_summery_page'),
    path('stock_analysis_page', views.stock_analysis_page, name='stock_analysis_page'),
    path('comparative_stock_analysis_page', views.comparative_stock_analysis_page, name='comparative_stock_analysis_page'),
    path('periodic_reports_page', views.periodic_reports_page, name='periodic_reports_page'),
    path('specified_reports_page', views.specified_reports_page, name='specified_reports_page'),


    # ajax
    path('ajax_stock_analysis', views.ajax_stock_analysis, name='ajax_stock_analysis'),
    path('ajax_transactions_summery', views.ajax_transactions_summery, name='ajax_transactions_summery'),
    path('ajax_comparative_stock_analysis', views.ajax_comparative_stock_analysis, name='ajax_comparative_stock_analysis'),
    
    path('get_data_for_day_end', views.get_data_for_day_end, name='get_data_for_day_end'),
    path('get_data_for_month_end', views.get_data_for_month_end, name='get_data_for_month_end'),
    path('get_data_for_year_end', views.get_data_for_year_end, name='get_data_for_year_end'),

    #   print out
    path('print_out_daily_transactions_summery', views.print_out_daily_transactions_summery, name='print_out_daily_transactions_summery'),
    path('print_data_for_day_end', views.print_data_for_day_end, name='print_data_for_day_end'),
    path('print_data_for_month_end', views.print_data_for_month_end, name='print_data_for_month_end'),
    path('print_data_for_year_end', views.print_data_for_year_end, name='print_data_for_year_end'),
    path('print_out_daily_transactions_per_invoice', views.print_out_daily_transactions_per_invoice, name='print_out_daily_transactions_per_invoice'),
    
    path('request_specified_report', views.request_specified_report, name='request_specified_report'),
    

    
    # fixies
    path('update_reorder_quanties_to/<int:pk>', views.update_reorder_quanties_to, name='update_reorder_quanties_to'),
    

    #   data backup
    path('create_backup', views.create_backup, name='create_backup'),    

    # data syncronization
    path('sync', views.sync, name='sync'),
    path('sync_current_stock_data', views.sync_current_stock_data, name='sync_current_stock_data'),
    path('sync_data_for_day_end', views.sync_data_for_day_end, name='sync_data_for_day_end'),    
    path('sync_data_for_month_end', views.sync_data_for_month_end, name='sync_data_for_month_end'),    
    path('sync_data_for_year_end', views.sync_data_for_year_end, name='sync_data_for_year_end'),

]