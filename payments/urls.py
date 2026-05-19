from django.urls import path
from .import views


urlpatterns = [
	# ajax
	#	update
	path('update_currency', views.update_currency, name='update_currency'),
	path('update_expense_type', views.update_expense_type, name='update_expense_type'),
	

	# 	options
	path('load_payment_method_options', views.load_payment_method_options, name='load_payment_method_options'),
	path('load_live_vat_code_options', views.load_live_vat_code_options, name='load_live_vat_code_options'),
	path('load_live_expense_type_options/', views.load_live_expense_type_options, name='load_live_expense_type_options'),

	# details
	# path('get_expense_type_details', views.get_expense_type_details, name='get_expense_type_details'),
	path('get_sale_details', views.get_sale_details, name='get_sale_details'),
	path('get_sale_transaction_details', views.get_sale_transaction_details, name='get_sale_transaction_details'),

	path('get_paying_currency_details', views.get_paying_currency_details, name='get_paying_currency_details'),
	path('get_currency_details', views.get_currency_details, name='get_currency_details'),
	path('get_expense_details', views.get_expense_details, name='get_expense_details'),
	path('get_expense_type_details', views.get_expense_type_details, name='get_expense_type_details'),

	path('reprint_receipt', views.reprint_receipt, name='reprint_receipt'),

	# list
	path('ajax_vat_codes_live_search', views.ajax_vat_codes_live_search, name='ajax_vat_codes_live_search'),
	path('ajax_currencies_live_search', views.ajax_currencies_live_search, name='ajax_currencies_live_search'),
	path('ajax_sales_live_search', views.ajax_sales_live_search, name='ajax_sales_live_search'),
	path('ajax_expense_types_live_search', views.ajax_expense_types_live_search, name='ajax_expense_types_live_search'),
	path('ajax_expenses_live_search', views.ajax_expenses_live_search, name='ajax_expenses_live_search'),
	path('ajax_transactions_live_search', views.ajax_transactions_live_search, name='ajax_transactions_live_search'),

	path('load_invoice_payment_portions_data', views.load_invoice_payment_portions_data, name='load_invoice_payment_portions_data'),

	# 	delete
	path('delete_invoice_money_portion', views.delete_invoice_money_portion, name='delete_invoice_money_portion'),
	path('delete_expense_money_portion', views.delete_expense_money_portion, name='delete_expense_money_portion'),
	path('delete_expense', views.delete_expense, name='delete_expense'),
	path('delete_expense_type', views.delete_expense_type, name='delete_expense_type'),

	#	add
	path('add_reciept_payment_portion/', views.add_reciept_payment_portion, name='add_reciept_payment_portion'),
	path('add_vat_code/', views.add_vat_code, name='add_vat_code'),
	path('add_currency/', views.add_currency, name='add_currency'),
	path('add_expense_type/', views.add_expense_type, name='add_expense_type'),
	path('add_expense/', views.add_expense, name='add_expense'),
	path('add_invoice_payment_portion', views.add_invoice_payment_portion, name='add_invoice_payment_portion'),
	path('add_invoice_money_portion_for_existing_invoice', views.add_invoice_money_portion_for_existing_invoice, name='add_invoice_money_portion_for_existing_invoice'),
	path('add_expense_money_portion', views.add_expense_money_portion, name='add_expense_money_portion'),
	path('add_credit_note_refund_money_portion', views.add_credit_note_refund_money_portion, name='add_credit_note_refund_money_portion'),
	path('add_return_out_refund_money_portion', views.add_return_out_refund_money_portion, name='add_return_out_refund_money_portion'),
	

	#	download
	path('download_simple_sales_filtered_sales_csv/', views.download_simple_sales_filtered_sales_csv, name='download_simple_sales_filtered_sales_csv'),
	path('download_sale_transactions_csv/', views.download_sale_transactions_csv, name='download_sale_transactions_csv'),
	

	
	# html pages
	

	path('sales_page', views.sales_page, name='sales_page'),
	path('sales_transactions_page', views.sales_transactions_page, name='sales_transactions_page'),

	path('expenses_page', views.expenses_page, name='expenses_page'),
	path('expense_types_page', views.expense_types_page, name='expense_types_page'),


	path('VATcodes_page', views.VATcodes_page, name='VATcodes_page'),
	path('payment_methods_page', views.payment_methods_page, name='payment_methods_page'),
]