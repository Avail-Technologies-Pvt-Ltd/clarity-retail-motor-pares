from django.urls import path
from .import views
from reusable_functions.univesal import notifications


urlpatterns = [

    # ajax
    #   options
    path('load_stock_options', views.load_stock_options, name='load_stock_options'),
    path('load_live_invoice_options', views.load_live_invoice_options, name='load_live_invoice_options'),
    path('load_live_stock_options', views.load_live_stock_options, name='load_live_stock_options'),
    path('load_live_product_options', views.load_live_product_options, name='load_live_product_options'),
    path('load_live_batch_adjustment_reason_options', views.load_live_batch_adjustment_reason_options, name='load_live_batch_adjustment_reason_options'),
    path('load_live_return_reason_options', views.load_live_return_reason_options, name='load_live_return_reason_options'),
    path('load_live_category_options', views.load_live_category_options, name='load_live_category_options'),
    path('load_live_department_options', views.load_live_department_options, name='load_live_department_options'),
    
    #   live search data
    path('ajax_departments_live_search', views.ajax_departments_live_search, name='ajax_departments_live_search'),
    path('ajax_categories_live_search', views.ajax_categories_live_search, name='ajax_categories_live_search'),
    path('ajax_notifications_live_search', views.ajax_notifications_live_search, name='ajax_notifications_live_search'),
    path('ajax_return_reasons_live_search', views.ajax_return_reasons_live_search, name='ajax_return_reasons_live_search'),
    path('ajax_invoices_live_search', views.ajax_invoices_live_search, name='ajax_invoices_live_search'),
    path('ajax_stock_live_search', views.ajax_stock_live_search, name='ajax_stock_live_search'),
    path('ajax_stock_prices_live_search', views.ajax_stock_prices_live_search, name='ajax_stock_prices_live_search'),
    path('ajax_products_live_search', views.ajax_products_live_search, name='ajax_products_live_search'),
    path('ajax_batches_live_search', views.ajax_batches_live_search, name='ajax_batches_live_search'),
    path('ajax_batch_adjustments_live_search', views.ajax_batch_adjustments_live_search, name='ajax_batch_adjustments_live_search'),
    path('ajax_stock_adjustment_reasons_live_search', views.ajax_stock_adjustment_reasons_live_search, name='ajax_stock_adjustment_reasons_live_search'),
    path('ajax_returns_out_live_search', views.ajax_returns_out_live_search, name='ajax_returns_out_live_search'),
    path('ajax_credit_note_live_search', views.ajax_credit_note_live_search, name='ajax_credit_note_live_search'),
    path('ajax_batch_adjustment_reasons_live_search', views.ajax_batch_adjustment_reasons_live_search, name='ajax_batch_adjustment_reasons_live_search'),
    path('request_notifications', views.request_notifications, name='request_notifications'),
    path('update_visible_stock_prices', views.update_visible_stock_prices, name='update_visible_stock_prices'),
    path('update_all_stock_prices', views.update_all_stock_prices, name='update_all_stock_prices'),
    
    

    #   details
    path('get_department_details', views.get_department_details, name='get_department_details'),
    path('get_category_details', views.get_category_details, name='get_category_details'),
    path('get_notification_details', views.get_notification_details, name='get_notification_details'),
    path('load_current_temporary_invoice', views.load_current_temporary_invoice, name='load_current_temporary_invoice'),
    path('load_temporary_invoice_preview_data', views.load_temporary_invoice_preview_data, name='load_temporary_invoice_preview_data'),

    path('get_invoice_details', views.get_invoice_details, name='get_invoice_details'),
    path('get_temporary_invoice_item_details', views.get_temporary_invoice_item_details, name='get_temporary_invoice_item_details'),
    path('get_stock_details', views.get_stock_details, name='get_stock_details'),
    path('get_batch_details', views.get_batch_details, name='get_batch_details'),
    path('get_return_out_details', views.get_return_out_details, name='get_return_out_details'),
    path('get_credit_note_details', views.get_credit_note_details, name='get_credit_note_details'),
    path('get_product_details', views.get_product_details, name='get_product_details'),
    
    path('get_reorder_suggestion_list', views.get_reorder_suggestion_list, name='get_reorder_suggestion_list'),
    path('print_out_order_list', views.print_out_order_list, name='print_out_order_list'),


    #   delete
    path('delete_category', views.delete_category, name='delete_category'),
    path('delete_department', views.delete_department, name='delete_department'),
    path('delete_temporary_invoice_item', views.delete_temporary_invoice_item, name='delete_temporary_invoice_item'),
    path('delete_notification', views.delete_notification, name='delete_notification'),
    path('delete_credit_note_refund_money_portion', views.delete_credit_note_refund_money_portion, name='delete_credit_note_refund_money_portion'),
    path('delete_return_out_refund_money_portion', views.delete_return_out_refund_money_portion, name='delete_return_out_refund_money_portion'),
    path('delete_product', views.delete_product, name='delete_product'),
    path('delete_batch_adjustment', views.delete_batch_adjustment, name='delete_batch_adjustment'),
    path('delete_batch_adjustment_reason', views.delete_batch_adjustment_reason, name='delete_batch_adjustment_reason'),
    path('delete_notifications', views.delete_notifications, name='delete_notifications'),
    path('delete_return_reason', views.delete_return_reason, name='delete_return_reason'),


    #   add
    path('add_batch_invoice_patching', views.add_batch_invoice_patching, name='add_batch_invoice_patching'),
    path('add_department', views.add_department, name='add_department'),
    path('add_category', views.add_category, name='add_category'),
    path('return_inn_sale_bulk', views.return_inn_sale_bulk, name='return_inn_sale_bulk'),
    path('return_inn_sale', views.return_inn_sale, name='return_inn_sale'),
    path('add_product', views.add_product, name='add_product'),
    path('add_batch_adjustment_reason', views.add_batch_adjustment_reason, name='add_batch_adjustment_reason'),
    path('add_return_reason', views.add_return_reason, name='add_return_reason'),
    
    path('create_batch_adjustment', views.create_batch_adjustment, name='create_batch_adjustment'),
    path('create_return_out', views.create_return_out, name='create_return_out'),


    #   edit
    path('update_department', views.update_department, name='update_department'),
    path('update_category', views.update_category, name='update_category'),
    path('update_temporary_invoice_item', views.update_temporary_invoice_item, name='update_temporary_invoice_item'),
    path('save_stock_adjustments', views.save_stock_adjustments, name='save_stock_adjustments'),
    path('activate_deactivate_batch', views.activate_deactivate_batch, name='activate_deactivate_batch'),
    path('update_product', views.update_product, name='update_product'),
    path('on_pos_change_price', views.on_pos_change_price, name='on_pos_change_price'),
    path('merge_products', views.merge_products, name='merge_products'),

    #   print
    path('print_out_credit_note', views.print_out_credit_note, name='print_out_credit_note'),
    path('print_all_stock_for_reconcile', views.print_all_stock_for_reconcile, name='print_all_stock_for_reconcile'),
    

    #   automated functions
    path('batch_expiration_notification', notifications.batch_expiration_notification, name='batch_expiration_notification'),



    path('get_stock_value_summary', views.get_stock_value_summary, name='get_stock_value_summary'),
    path('print_out_stock_summary_to_pos', views.print_out_stock_summary_to_pos, name='print_out_stock_summary_to_pos'),


    # html pages
    path('departments_page', views.departments_page, name='departments_page'),
    path('categories_page', views.categories_page, name='categories_page'),
    path('notifications_page', views.notifications_page, name='notifications_page'),
    path('invoices_page', views.invoices_page, name='invoices_page'),
    path('lables_page', views.lables_page, name='lables_page'),
    path('returns_out_page', views.returns_out_page, name='returns_out_page'),
    path('return_reasons_page', views.return_reasons_page, name='return_reasons_page'),
    path('credit_notes_page/', views.credit_notes_page, name='credit_notes_page'),

    path('products_page/', views.products_page, name='products_page'),
    path('stocks_page/', views.stocks_page, name='stocks_page'),
    path('notifications_page/', views.notifications_page, name='notifications_page'),
    path('batches_page/', views.batches_page, name='batches_page'),
    path('batch_adjustments_page/', views.batch_adjustments_page, name='batch_adjustments_page'),
    path('batch_adjustment_reasons_page/', views.batch_adjustment_reasons_page, name='batch_adjustment_reasons_page'),
    path('mass_price_adjustments_page/', views.mass_price_adjustments_page, name='mass_price_adjustments_page'),



    # none serialized links
    path('add_temporary_invoice_item/', views.add_temporary_invoice_item, name='add_temporary_invoice_item'),
    path('get_temporary_invoice_items_for_preview/', views.get_temporary_invoice_items_for_preview, name='get_temporary_invoice_items_for_preview'),
    path('delete_temporary_invoice/', views.delete_temporary_invoice, name='delete_temporary_invoice'),
    path('add_temporary_invoice_to_stock/', views.add_temporary_invoice_to_stock, name='add_temporary_invoice_to_stock'),
    path('add_temporary_invoice/', views.add_temporary_invoice, name='add_temporary_invoice'),

    path('request_current_temporary_invoice/', views.request_current_temporary_invoice, name='request_current_temporary_invoice'),
]
