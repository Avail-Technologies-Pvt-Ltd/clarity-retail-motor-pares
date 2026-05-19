from django.urls import path
from .import views


urlpatterns = [
	path('pos/', views.pos, name='pos'),

	# ajax
	path('add_stock_to_cart/', views.add_stock_to_cart, name='add_stock_to_cart'),
	path('load_cart_data/', views.load_cart_data, name='load_cart_data'),
	path('load_receipt_payment_portions_data/', views.load_receipt_payment_portions_data, name='load_receipt_payment_portions_data'),
	path('void_payment/', views.void_payment, name='void_payment'),
	path('delete_cart_item/', views.delete_cart_item, name='delete_cart_item'),
	path('void_cart/', views.void_cart, name='void_cart'),


	path('get_quotation_data/', views.get_quotation_data, name='get_quotation_data'),
	
	path('reprint_user_last_receipt/', views.reprint_user_last_receipt, name='reprint_user_last_receipt'),
	

	
	# APIs
	path('check_out/', views.check_out, name='check_out'),

	# Explucively qutations
	path('ajax_quotations_live_search/', views.ajax_quotations_live_search, name='ajax_quotations_live_search'),
	path('quotations_page/', views.quotations_page, name='quotations_page'),
	path('create_quotation_page/<int:pk>', views.create_quotation_page, name='create_quotation_page_with_pk'),
	path('create_quotation_page/', views.create_quotation_page, name='create_quotation_page'),
	path('add_quotation_item/', views.add_quotation_item, name='add_quotation_item'),
	path('get_quotation_data_exclusive/', views.get_quotation_data_exclusive, name='get_quotation_data_exclusive'),
    path('delete-quotation-item/', views.delete_quotation_item, name='delete_quotation_item'),
    path('clear-quotation-items/', views.clear_quotation_items, name='clear_quotation_items'),
    path('quotation-print/', views.quotation_print_view, name='quotation_print'),
    path('print_quotation_in_pos_printer/', views.print_quotation_in_pos_printer, name='print_quotation_in_pos_printer'),
    path('copy_quotation_to_cart/', views.copy_quotation_to_cart, name='copy_quotation_to_cart'),
]