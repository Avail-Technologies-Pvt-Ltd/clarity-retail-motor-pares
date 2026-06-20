from django.shortcuts import render

import json
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse

from payments.models import *
from enventory.models import *
from accounts.models import ClientSetting

from datetime import datetime as datetime_
import datetime

from dateutil.relativedelta import relativedelta

from django.db import transaction
from django.db.models import Sum, Expression, DecimalField, F, Q

import locale
locale.setlocale(locale.LC_ALL, '') 

from reusable_functions.univesal.decorators import role_validator
from django.contrib.auth.decorators import login_required

import random

from reusable_functions.univesal.client_spacific_functions.client_spacific_functions import  print_formated_text
from reusable_functions.univesal.reporting import calculate_net
from reusable_functions.univesal.reporting import group_money_portions_into_dict, group_money_portions_by_payment_methods
from reusable_functions.univesal.periodic_reports import get_day_end_summary

import calendar

# import requests

try:
    configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
    pagination_slice_leangth = configuration.pagination_slice_leangth
except Exception as e:
    HttpResponseRedirect('client_settings_page')


@login_required
def periodic_reports_page(request):
	configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]

	context = {
		"last_sync_time": configuration.last_sync_time,
		"last_sync_user": configuration.last_sync_user,
	}
	return render(request, 'reports/sales_history/periodic_reports_page.html', context)

@login_required
def specified_reports_page(request):
	return render(request, 'reports/sales_history/specified_reports_page.html')

@login_required
def stock_analysis_page(request):
	return render(request, 'reports/sales_history/analysis/stock_analysis_page.html')

@login_required
def transactions_summery_page(request):
	return render(request, 'reports/sales_history/transactions_summery_page.html')


@login_required
def comparative_stock_analysis_page(request):
	return render(request, 'reports/sales_history/analysis/comparative_stock_analysis_page.html')




def sync(dict_data):
	import requests
	url = configuration.sync_url
	print(url)

	data = dict_data
	

	headers = {'Content-Type': 'application/json', 'CSRF cookie': "cookie"}
	custome_status = ""

	try:
		response = requests.post(url, data= json.dumps(data))
	except requests.exceptions.ConnectionError as e:
		message = "Unable to connect to the server. Please check your internet connection."
		custome_status = "Error"
	except requests.exceptions.Timeout as e:
		message = "Request timed out. Please try again later."
		custome_status = "Error"
	except requests.exceptions.RequestException as e:
		message = f"An error occurred while sending data: {str(e)}"
		custome_status = "Error"
	except Exception as e: 
		message = "An unexpected error occurred." 
		custome_status = "Error"


	if custome_status == "Error":
		return custome_status, message


	if response.status_code == 200:
		print("Data sent succ...")
		custome_status = f"{ response.json()['custome_status'] }"
		message = f"{ response.json()['message'] }"
	else:
		custome_status = "Error"
		message = f"Error sending data {response.text}"


	return custome_status, message






@login_required
def request_specified_report(request):
# 	user_id = request.GET.get('user')
# 	date_from = request.GET.get('date_from')
# 	date_to = request.GET.get('date_to')
# 	detail = request.GET.get('detail')
# 	aspect = request.GET.get('aspect')
# 	action = request.GET.get('action')

# 	try:
# 		user = User.objects.get(id=int(user_id))
# 		user_name_text = f"{ user.first_name } { user.first_name } ({ user.username })"
# 	except:
# 		user_name_text = "All Users"

# 	if aspect == "Sales Invoices":
# 		transactions = SaleTransaction.objects.all()
# 		if date_from:
# 			transactions = transactions.filter(created_at__date__gte=date_from)
# 		if date_to:
# 			transactions = transactions.filter(created_at__date__lte=date_to)
# 		if user_id != "all":
# 			transactions = transactions.filter(created_by__id=int(user_id))

# 		if action == "Print Out":

# 			if detail == "Summery":

# 				# variables
# 				time_frame = f"{ date_from } - { date_to }"
# 				total_invoices = transactions.count()
# 				total_sales = 0
# 				for transaction in transactions:
# 					total_sales += Sale.objects.filter(sale_transaction=transaction).count()


# 				text = f"""{ aspect } { detail } Report.
# ----------------------------------------------
# OPERATOR            : { user_name_text }
# TIME FRAME          : { time_frame }
# TOTAL SALES INVOICES: { total_invoices }
# TOTAL SALES         : { total_invoices }
# ----------------------------------------------
# CURRENCY	AMOUNT 			VALUE
# """
# 				receiptmoneyportions = ReceiptMoneyPortion.objects.filter(sale_transaction__in=transactions)

# 				money_portions = group_money_portions_by_payment_methods(receiptmoneyportions, "ReceiptMoneyPortion")

# 				unique_keys = list(set(money_portions.keys()))
				
# 				for key in unique_keys:
# 					text += f"""{ money_portions[key][0] }		{ locale.format_string('%2f', float(money_portions[key][1]), grouping=True) }	{ locale.format_string('%2f', float(money_portions[key][2]), grouping=True) } \n"""


# 				custome_status, message = print_formated_text(text)
# 				print(text)

# 				return JsonResponse({ 'custome_status': custome_status, 'message': message })


# 			else:	# DETAILED REPORT
# 				# variables
# 				time_frame = f"{ date_from } - { date_to }"
# 				total_invoices = transactions.count()
# 				total_sales = 0
# 				for transaction in transactions:
# 					total_sales += Sale.objects.filter(sale_transaction=transaction).count()


# 				text = f"""{ aspect } { detail } Report.
# ----------------------------------------------
# OPERATOR            : { user_name_text }
# TIME FRAME          : { time_frame }
# TOTAL SALES INVOICES: { total_invoices }
# TOTAL SALES         : { total_invoices }
# ----------------------------------------------
# CURRENCY	AMOUNT 			VALUE
# """
# 				receiptmoneyportions = ReceiptMoneyPortion.objects.filter(sale_transaction__in=transactions)

# 				money_portions = group_money_portions_by_payment_methods(receiptmoneyportions, "ReceiptMoneyPortion")

# 				unique_keys = list(set(money_portions.keys()))
				
# 				for key in unique_keys:
# 					text += f"""{ money_portions[key][0] }		{ locale.format_string('%2f', float(money_portions[key][1]), grouping=True) }	{ locale.format_string('%2f', float(money_portions[key][2]), grouping=True) } \n"""

# 				# print(text)
# 				invoices_text = ""
# 				transaction_text = ""
# 				for transaction in transactions:
# 					lines_text = ""
# 					sales = Sale.objects.filter(sale_transaction=transaction)
# 					for sale in sales:
# 						title_and_quantity = f"{sale.quantity} x ({str(sale.stock.product.product_code)}) {str(sale.stock.product.title)} "
# 						lines_text += f"    {title_and_quantity[:30]:<30}  {round(sale.unit_price * sale.quantity,2) :>10}\n"

# 					money_portions = ReceiptMoneyPortion.objects.filter(sale_transaction=transaction)
# 					money_portion_text = "    CURRENCY		  AMOUNT         VALUE"
# 					for money_portion in money_portions:
# 						money_portion_text += f"\n    {money_portion.payment_method.shortcut:<17} {round(money_portion.amount_paid, 2):>10} {money_portion.rated_amount:>13}"



# 					transaction_text = f"""
# **********************************************
# INVOICE NUMBER: #: {transaction.ultimate_recipt_number}
# Buyer:{transaction.buyer_name}
# BY   :{transaction.created_by.first_name.title()} {transaction.created_by.last_name.title()}
# ----------------------------------------------
# {lines_text}
#     {'SUBTOTAL':<32}{ locale.format_string('%.2f', transaction.totals['subtotal'], grouping=True) :>10}
#     {'DISCOUNT':<32}{ locale.format_string('%.2f', transaction.discount, grouping=True) :>10}
#     {'VAT':<32}{ locale.format_string('%.2f', transaction.totals['VAT'], grouping=True) :>10}
#     {'TOTAL COST':<32}{ locale.format_string('%.2f', transaction.totals['total_cost'], grouping=True) :>10}
#     ------------------------------------------
# {money_portion_text}
#     ------------------------------------------
# 		"""

# 					invoices_text += transaction_text
# 				text += f"""
# ----------------------------------------------
# { invoices_text }
# """
# 				print(text)
# 				custome_status, message = print_formated_text(text)

# 				return JsonResponse({ 'custome_status': custome_status, 'message': message })




# 		else:
# 			pass


	return 0


@login_required
def ajax_comparative_stock_analysis(request):
	# print("Running")
	date_from = request.GET.get("date_from")[:10]
	date_to = request.GET.get("date_to")[:10]
	scale = request.GET.get("scale")
	aspect = request.GET.get("aspect")
	total = request.GET.get("total")
	graph_type = request.GET.get("graph_type")

	date_from = date_from + " 00:00:00.000000+00:00"
	date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S.%f%z')

	date_to = date_to + " 00:00:00.000000+00:00"
	date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S.%f%z')



	if scale == "Daily":
		scale = relativedelta(days=1)
	elif scale == "Weekely":
		scale = relativedelta(weeks=1)
	elif scale == "Monthly":
		scale = relativedelta(months=1)
	elif scale == "Anualy":
		scale = relativedelta(years=1)



	summery_text = ""

	if aspect == "Profit (Top)":
		# ---------------------------------------------------------------------------------------------------
		''' i have Stock model and Sale model, Sale has a field stock that is a foreign key (Stock). in Sale there are also
			fields: buying_price and selling_price and quantity wich are used to calculate profit (selling_price - buying_price) * quantity. 
			Using django query i want to calculate and add profits for all sales that have the same stock field. arrange the Stocks ordered
			by most profiting then take only top 10.
		'''
		stock_of_intrest_list = Stock.objects.filter(sale__created_at__range=(date_from, date_to)).annotate(
		total_profit=Sum((F('sale__selling_price') - F('sale__buying_unit_price')) * F('sale__quantity'))
		).order_by('-total_profit')[:int(total)]

		summery_text = f"""
					<h5>Top {len(stock_of_intrest_list)} most profiting from {str(date_from)[:10]} to {str(date_to)[:10]}. <small>TOP PROFITING</small></h5>
					<table class="table table-hover">
						<tr >
							<th style='min-width: 20px'>#</th>
							<th>Stock</th>
							<th style='right; padding-left: 40px'>Total Profit(USD)</th>
						</tr>
						"""

		list_counter = 1
		for stock in stock_of_intrest_list:
			summery_text += f"""
									<tr>
										<td>{list_counter}</td>
										<td>{stock.product.title} {stock.product.details}</td>
										<td style='text-align: right; padding-left: 40px'>{(locale.format_string('%.2f', stock.total_profit, grouping=True))}</td> 
									</tr>
								
							 """
										
			# print(f"Stock ID: {stock.id}, Total Profit: {stock.total_profit}")
			list_counter += 1



	elif aspect == "Total Sales (Top)":
		stock_of_intrest_list = Stock.objects.filter(sale__created_at__range=(date_from, date_to)).annotate(total_sales=Sum('sale__quantity')).order_by('-total_sales')[:int(total)]

		summery_text = f"""
					<h5>Top {len(stock_of_intrest_list)} most selling from {str(date_from)[:10]} to {str(date_to)[:10]}. <small>TOP SELLING</small></h5>
					<table class="table table-hover">
						<tr >
							<th style='min-width: 20px'>#</th>
							<th>Stock</th>
							<th style='right; padding-left: 40px'>Total Sales</th>
						</tr>
						"""

		list_counter = 1
		for stock in stock_of_intrest_list:
			summery_text += f"""
									<tr>
										<td>{list_counter}</td>
										<td>{stock.product.title} {stock.product.details} </td>
										<td style='text-align: right; padding-left: 40px'>{(locale.format_string('%.2f', stock.total_sales, grouping=True))}</td> 
									</tr>
								
							 """
										
			# print(f"Stock ID: {stock.id}, Total Profit: {stock.total_sales}")
			list_counter += 1


	elif aspect == "Sales Value (Top)":
		stock_of_intrest_list = Stock.objects.filter(sale__created_at__range=(date_from, date_to)).annotate(
		total_sales_value=Sum((F('sale__selling_price')) * F('sale__quantity'))
		).order_by('-total_sales_value')[:int(total)]

		summery_text = f"""
					<h5>Top {len(stock_of_intrest_list)} with most sales value from {str(date_from)[:10]} to {str(date_to)[:10]}. <small>TOP SALES VALUE</small></h5>
					<table class="table table-hover">
						<tr >
							<th style='min-width: 20px'>#</th>
							<th>Stock</th>
							<th style='right; padding-left: 40px'>Total Sales Value(USD)</th>
						</tr>
						"""

		list_counter = 1
		for stock in stock_of_intrest_list:
			summery_text += f"""
									<tr>
										<td>{list_counter}</td>
										<td>{stock.product.title} {stock.product.details} </td>
										<td style='text-align: right; padding-left: 40px'>{(locale.format_string('%.2f', stock.total_sales_value, grouping=True))}</td> 
									</tr>
								
							 """
										
			# print(f"Stock ID: {stock.id}, Total Profit: {stock.total_sales_value}")
			list_counter += 1


	summery_text += """ </table> """


	# ---------------------------------------------------------------------------------------------------
	labels = []
	stock_values_dict = {}

	while date_from <= date_to:
		labels.append(str(date_from)[:10])
		if aspect == "Profit (Top)":
			for stock in stock_of_intrest_list:
				# Get all Sale instances for the current stock
				sales = Sale.objects.filter(stock=stock, created_at__gte=date_from, created_at__lte=date_from+scale)

				# Calculate the profit for each sale and sum them up
				selected_time_slot_stock_total_profit =  sum((sale.selling_price - sale.buying_unit_price) * sale.quantity for sale in sales)
				current_stock_id = f"stock_id_{stock.id}"
				
				if current_stock_id in stock_values_dict:
					# the stock id alredy exist
					pass
				else:
					# create a new empty dictionary value for the current stock
					stock_values_dict[current_stock_id] = []

				# append the value in to a list of values. The dates are being stored pararel to values lists in lables
				stock_values_dict[current_stock_id].append(float(selected_time_slot_stock_total_profit))


		elif aspect == "Total Sales (Top)":
			for stock in stock_of_intrest_list:
				# Get all Sale instances for the current stock
				sales = Sale.objects.filter(stock=stock, created_at__gte=date_from, created_at__lte=date_from+scale)

				# Calculate the total sales for each stock
				selected_time_slot_stock_total_sales =  sales.count()
				current_stock_id = f"stock_id_{stock.id}"
				
				if current_stock_id in stock_values_dict:
					# the stock id alredy exist
					pass
				else:
					# create a new empty dictionary value for the current stock
					stock_values_dict[current_stock_id] = []

				# append the value in to a list of values. The dates are being stored pararel to values lists in lables
				stock_values_dict[current_stock_id].append(float(selected_time_slot_stock_total_sales))


		elif aspect == "Sales Value (Top)":
			for stock in stock_of_intrest_list:
				# Get all Sale instances for the current stock
				sales = Sale.objects.filter(stock=stock, created_at__gte=date_from, created_at__lte=date_from+scale)

				# Calculate the profit for each sale and sum them up
				selected_time_slot_stock_total_profit =  sum((sale.selling_price) * sale.quantity for sale in sales)
				current_stock_id = f"stock_id_{stock.id}"
				
				if current_stock_id in stock_values_dict:
					# the stock id alredy exist
					pass
				else:
					# create a new empty dictionary value for the current stock
					stock_values_dict[current_stock_id] = []

				# append the value in to a list of values. The dates are being stored pararel to values lists in lables
				stock_values_dict[current_stock_id].append(float(selected_time_slot_stock_total_profit))


		#data increamenting 
		date_from += scale



	datasets = []
	counter = 0
	for stock_id in stock_values_dict.keys():
		datasets.append({
			'label': stock_of_intrest_list[counter].product.title,
			'data': stock_values_dict[stock_id],
			'borderColor': "rgba(" + ','.join(['255', str(random.randint(0, 255)), str(random.randint(0, 255))]) + ", 1",
			'backgroundColor': "transparent"
			})

		counter += 1

	#=========================================================


	return JsonResponse({"labels": labels, "datasets":datasets, "summery_text":summery_text})





@login_required
@role_validator(['Data Analyst','Supervisor','Sales Rep'])
def ajax_transactions_summery(request):
	filter_date = request.GET.get('filter_date')

	sales_profit = 0
	number_of_sales = 0
	sales_value = 0
	expenses_value = 0
	total_returns_inn = 0
	total_returns_out = 0
	received_stock_value = 0
	stock_value = 0
	return_inn_refunds_amount = 0
	return_out_refunds_amount = 0

	# SALES
	sales = Sale.objects.filter(created_at__date=filter_date, deleted=False)
	# print(sales)
	for sale in sales:
		sales_profit += sale.profit
		sales_value += sale.total_price

	number_of_sales = sales.count()

	#EXPENSES
	expenses = Expense.objects.filter(created_at__date=filter_date, deleted=False)
	for expense in expenses:
		expenses_value += expense.price

	#RETURNS INN
	returns_inn = ReturnInn.objects.filter(created_at__date=filter_date, deleted=False)
	total_returns_inn = returns_inn.count()
	
	#-- for deducting the profit of the filter date. Focuses on the returns of the sales of the filter date not returns of the filter date
	date_sales_returns = ReturnInn.objects.filter(sale__created_at__date=filter_date)
	for a in date_sales_returns:
		return_inn_refunds_amount += a.refund_amount


	#accounting for returns inn
	sales_profit = float(sales_profit) #- float(return_inn_refunds_amount)

	#RETURNS OUT
	returns_out = ReturnOut.objects.filter(created_at__date=filter_date, deleted=False)
	total_returns_out = returns_out.count()


	#-- for accounting refunds for returns out
	invoice_returns_out = ReturnOut.objects.filter(batch__invoice__date=filter_date)
	for a in invoice_returns_out:
		return_out_refunds_amount += a.refund_amount


	#BATCHIES
	batches = Batch.objects.filter(created_at__date=filter_date, deleted=False)
	for batch in batches:
		received_stock_value += batch.stock.selling_price * batch.total_units_bought
		stock_value += batch.batch_value


	if filter_date != str(datetime_.today().date())[:10]:
		stock_value = "xxx.xx"
	else:
		stock_value = locale.format_string('%.2f', stock_value, grouping=True)

	total_profit = float(sales_profit) - float(expenses_value)


	summery_details = {
		"total_profit": locale.format_string('%.2f', total_profit, grouping=True),
		"number_of_sales": locale.format_string('%.0f', number_of_sales, grouping=True),
		"sales_value": locale.format_string('%.2f', sales_value, grouping=True),
		"sales_profit": locale.format_string('%.2f', sales_profit, grouping=True),
		"expenses_value": locale.format_string('%.2f', expenses_value, grouping=True),
		"total_returns_inn": locale.format_string('%.0f', total_returns_inn, grouping=True),
		"total_returns_out": locale.format_string('%.0f', total_returns_out, grouping=True),
		"received_stock_value": locale.format_string('%.2f', received_stock_value, grouping=True),
		"return_inn_refunds_amount": locale.format_string('%.2f', return_inn_refunds_amount, grouping=True),
		"return_out_refunds_amount": locale.format_string('%.2f', return_out_refunds_amount, grouping=True),
		"stock_value": stock_value
	}

	# balancing money portions
	# income
	# receiptmoneyportions = ReceiptMoneyPortion.objects.filter(created_at__date=filter_date)
	receiptmoneyportions = Payment.objects.filter(payment_for="RECEIPT", date__date=filter_date)
	# refundreturnoutmoneyportions = RefundReturnOutMoneyPortion.objects.filter(created_at__date=filter_date)
	refundreturnoutmoneyportions = Payment.objects.filter(payment_for="RETURN_OUT_REFUND", date__date=filter_date)
	# expenses
	# invoicemoneyportions = InvoiceMoneyPortion.objects.filter(created_at__date=filter_date)
	invoicemoneyportions = Payment.objects.filter(payment_for="INVOICE", date__date=filter_date)
	# expensemoneyportions = ExpenseMoneyPortion.objects.filter(created_at__date=filter_date)
	expensemoneyportions = Payment.objects.filter(payment_for="EXPENSE", date__date=filter_date)
	# refundreturninnmoneyportions = RefundReturnInnMoneyPortion.objects.filter(created_at__date=filter_date)
	refundreturninnmoneyportions = Payment.objects.filter(payment_for="CREDIT_NOTE", created_at__date=filter_date)

	income_currencies, expenses_currencies = group_money_portions_into_dict(receiptmoneyportions, refundreturnoutmoneyportions, invoicemoneyportions, expensemoneyportions, refundreturninnmoneyportions)

	# BALANCING
	income_currencies, expenses_currencies, totals_dict = calculate_net(income_currencies, expenses_currencies) #gets income payments by curency dictionary and expenses the returns 3rd dict of totals or profit/los for every currency
	# print('@@@@@@@@@@@')
	# print(income_currencies)
	# print(expenses_currencies)
	# print(totals_dict)
	# -------------------------------------------------------------------------------------------------------------------------

	if len(totals_dict) == 0:# and len(invoice_money_portions) == 0 and len(expense_money_portions) == 0:
		payments_table = f"""
			<tr>
                <th style="text-align: center; color: red;">No Payments for this day</th>
            </tr>
		"""
	else: 
		# creating table header
		payments_table = """
			<tr>
                <th>Payment Method</th>
                <th colspan="3">Amount Paid</th>
                <th colspan="3">Rated Value</th>
            </tr>
            <tr>
                <th></th>
                <td style="text-align: right; color: blue;"><i>income</i></td>
                <td style="text-align: right; color: red;"><i>expenses</i></td>
                <td style="text-align: right; color: black;"><i><b>total</b></i></td>
                <td style="text-align: right; color: blue;"><i>income</i></td>
                <td style="text-align: right; color: red;"><i>expenses</i></td>
                <td style="text-align: right;"><h5>Total Value</h5></td>
            </tr>
		"""

		total_income_rated_value = 0
		total_expense_rated_value = 0
		total_total_value = 0
		#body
		for key in totals_dict.keys():
			payments_table += f"""
				<tr>
	                <th>{ totals_dict[key][0] }</th>
	                <td style="text-align: right; color: blue;">{ locale.format_string('%.2f', float(income_currencies[key][1]), grouping=True) }</td>
	                <td style="text-align: right; color: red;">({ locale.format_string('%.2f', float(expenses_currencies[key][1]), grouping=True) })</td>
	                <td style="text-align: right; color: black;"><b>{ locale.format_string('%.2f', float(totals_dict[key][1]), grouping=True) }</b></td>
	                <td style="text-align: right; color: blue;">{ locale.format_string('%.2f', float(income_currencies[key][2]), grouping=True) }</td>
	                <td style="text-align: right; color: red;">({ locale.format_string('%.2f', float(expenses_currencies[key][2]), grouping=True) })</td>
	                <td style="text-align: right; color: ;"><h4>{ locale.format_string('%.2f', float(totals_dict[key][2]), grouping=True) }</h4></td>
	            </tr>
			"""
			total_income_rated_value += float(income_currencies[key][2])
			total_expense_rated_value += float(expenses_currencies[key][2])
			total_total_value += float(totals_dict[key][2])
		#footer
		payments_table += f"""
			<tr>
                <th colspan="4">Total</th>
                <th style="text-align: right; color: blue"><u>{ locale.format_string('%.2f', total_income_rated_value, grouping=True) }</u></th>
                <th style="text-align: right; color: red;"><u>({ locale.format_string('%.2f', total_expense_rated_value, grouping=True) }</u>)</th>
                <th style="text-align: right;"><h3><u>{ locale.format_string('%.2f', total_total_value, grouping=True) }</u></h3></th>
            </tr>
		"""	

	return JsonResponse({"summery_details": summery_details, "payments_table": payments_table})



@login_required
def ajax_stock_analysis(request):
	from_filter = request.GET.get('date_from')
	to_filter = request.GET.get('date_to')
	interval = request.GET.get('scale')
	stock_id = request.GET.get('stock_id')

	# interprate received data
	from_filter = from_filter + " 00:00:00.000000+00:00"
	from_filter = datetime.datetime.strptime(from_filter, '%Y-%m-%d %H:%M:%S.%f%z')

	to_filter = to_filter + " 00:00:00.000000+00:00"
	to_filter = datetime.datetime.strptime(to_filter, '%Y-%m-%d %H:%M:%S.%f%z')

	stock_filter = Stock.objects.get(id=int(stock_id))
	if interval == "Daily":
		interval = relativedelta(days=1)
	elif interval == "Weekely":
		interval = relativedelta(weeks=1)
	elif interval == "Monthly":
		interval = relativedelta(months=1)
	elif interval == "Anualy":
		interval = relativedelta(years=1)


	# global variables
	dates_list = []

	sales_profit_list = []
	total_sales_profit = 0

	total_sale_list = [] #the least of total sales per interval
	total_sales = 0 #combined number of sales for all the intervals

	total_sales_value_list = []
	total_sales_value = 0

	total_returns_inn_list = []
	total_returns_out = 0

	total_returns_out_list = []
	total_returns_inn = 0

	received_stock_value_list = []
	received_stock_value = 0

	received_stock_units_list = []
	received_stock_units = 0





	# interval filtering
	while from_filter <= to_filter:
		# 
		end_f_date = from_filter + interval + relativedelta(days=1)
		from_f_date = from_filter
		dates_list.append(f"{str(from_f_date)[:10]}")

		# collecting data

		# 	profit
		sales = Sale.objects.filter(created_at__gte=from_f_date, created_at__lte=end_f_date, stock=stock_filter)
		sales_profit = 0
		total_sale_list.append(round(sales.count(), 2))
		total_sales += sales.count()
		for sale in sales:
			sales_profit += float(sale.profit)
			total_sales_value += float(sale.total_price)
		sales_profit_list.append(round(sales_profit, 2))
		total_sales_profit += sales_profit
		total_sales_value_list.append(round(total_sales_value, 2))

		# 	returns inn
		returns_inn = ReturnInn.objects.filter(created_at__gte=from_f_date, created_at__lte=end_f_date, stock=stock_filter)
		total_returns_inn_list.append(returns_inn.count())
		total_returns_inn += returns_inn.count()

		# 	returns out
		returns_out = ReturnOut.objects.filter(created_at__gte=from_f_date, created_at__lte=end_f_date, batch__stock=stock_filter)
		total_returns_out_list.append(returns_out.count()) 
		total_returns_out += returns_out.count()
		#	received stock
		received_stocks = InvoiceItem.objects.filter(invoice__created_at__gte=from_f_date, invoice__created_at__lte=end_f_date, stock=stock_filter)
		r_stock_value = 0
		for received_stock in received_stocks:
			r_stock_value += float(received_stock.stock_value)
		received_stock_value += r_stock_value
		received_stock_value_list.append(round(r_stock_value, 2))
		received_stock_units_list.append(received_stocks.count())
		received_stock_units += received_stocks.count()



		# incrementing while condition
		from_filter = from_filter + interval

	details = {
		# lists
		'dates_list': dates_list,
		'sales_profit_list': sales_profit_list,
		'total_sale_list': total_sale_list,
		'total_sales_value_list': total_sales_value_list,
		'total_returns_inn_list': total_returns_inn_list,
		'total_returns_out_list': total_returns_out_list,
		'received_stock_value_list': received_stock_value_list,
		'received_stock_units_list': received_stock_units_list,

		# solid variables
		'total_sales_profit': locale.format_string('%.2f', total_sales_profit, grouping=True),
		'total_sales': locale.format_string('%.0f', total_sales, grouping=True),
		'total_sales_value': locale.format_string('%.2f', total_sales_value, grouping=True),
		'received_stock_value': locale.format_string('%.2f', received_stock_value, grouping=True),
		'received_stock_units': locale.format_string('%.0f', received_stock_units, grouping=True),
		'total_returns_out': locale.format_string('%.0f', total_returns_out, grouping=True),
		'total_returns_inn': locale.format_string('%.0f', total_returns_inn, grouping=True),
	}

	return JsonResponse({'details': details})






def print_out_daily_transactions_per_invoice(request):
	filter_date = request.GET.get('filter_date')
	filter_date_from = filter_date
	filter_date_to = filter_date

	transactions = SaleTransaction.objects.filter(created_at__date__range=(filter_date_from, filter_date_to))

	invoices_text = ""
	transaction_text = ""
	for transaction in transactions:
		lines_text = ""
		sales = Sale.objects.filter(sale_transaction=transaction)
		for sale in sales:
			title_and_quantity = f"{sale.quantity} x ({str(sale.stock.product.product_code)}) {str(sale.stock.product.title)} "
			lines_text += f"    {title_and_quantity[:30]:<30}  {round(sale.unit_price * sale.quantity,2) :>10}\n"

		# money_portions = ReceiptMoneyPortion.objects.filter(sale_transaction=transaction)
		money_portions = Payment.objects.filter(payment_for="RECEIPT", payment_for_id=transaction.recipt_number)
		money_portion_text = "    CURRENCY		  AMOUNT         VALUE"
		for money_portion in money_portions:
			money_portion_text += f"\n    {money_portion.payment_method.shortcut:<17} {round(money_portion.amount_paid, 2):>10} {money_portion.rated_value:>13}"


		transaction_text = f"""
**********************************************
INVOICE NUMBER: #: {transaction.ultimate_recipt_number}
Buyer:{transaction.buyer_name}
BY   :{transaction.created_by.first_name.title()} {transaction.created_by.last_name.title()}
----------------------------------------------
{lines_text}
    {'SUBTOTAL':<32}{ locale.format_string('%.2f', transaction.totals['subtotal'], grouping=True) :>10}
    {'DISCOUNT':<32}{ locale.format_string('%.2f', transaction.discount, grouping=True) :>10}
    {'VAT':<32}{ locale.format_string('%.2f', transaction.totals['VAT'], grouping=True) :>10}
    {'TOTAL COST':<32}{ locale.format_string('%.2f', transaction.totals['total_cost'], grouping=True) :>10}
    ------------------------------------------
{money_portion_text}
    ------------------------------------------
		"""

		invoices_text += transaction_text
	text = f"""
----------------------------------------------
DAILY SALES PER INVOICE
DATE: { filter_date }
TOTAL NUMBER OF INVOICES: { transactions.count() }
----------------------------------------------

{ invoices_text }
"""
	print(text)
	custome_status, message = print_formated_text(text)
	return JsonResponse({"custome_status": custome_status, "message": message,})



def print_out_daily_transactions_summery(request):
	filter_date = request.GET.get('filter_date')

	sales_profit = request.GET.get('sales_profit')
	number_of_sales = request.GET.get('number_of_sales')
	sales_value = request.GET.get('sales_value')
	expenses_value = request.GET.get('expenses_value')
	total_returns_inn = request.GET.get('total_returns_inn')
	total_returns_out = request.GET.get('total_returns_out')
	received_stock = request.GET.get('received_stock')
	total_profit = request.GET.get('total_profit')

	# cash_in_hand_list = []

	# income---------------------
	# receiptmoneyportions = ReceiptMoneyPortion.objects.filter(created_at__date=filter_date)
	receiptmoneyportions = Payment.objects.filter(payment_for="RECEIPT", date__date=filter_date)
	# refundreturnoutmoneyportions = RefundReturnOutMoneyPortion.objects.filter(created_at__date=filter_date)
	refundreturnoutmoneyportions = Payment.objects.filter(payment_for="RETURN_OUT_REFUND", created_at__date=filter_date)
	# expenses------------------------
	# invoicemoneyportions = InvoiceMoneyPortion.objects.filter(created_at__date=filter_date)
	invoicemoneyportions = Payment.objects.filter(payment_for="INVOICE", date__date=filter_date)
	# expensemoneyportions = ExpenseMoneyPortion.objects.filter(created_at__date=filter_date)
	expensemoneyportions = Payment.objects.filter(payment_for="EXPENSE", date__date=filter_date)
	# refundreturninnmoneyportions = RefundReturnInnMoneyPortion.objects.filter(created_at__date=filter_date)
	refundreturninnmoneyportions = Payment.objects.filter(payment_for="CREDIT_NOTE", created_at__date=filter_date)

	income_currencies, expenses_currencies = group_money_portions_into_dict(receiptmoneyportions, refundreturnoutmoneyportions, invoicemoneyportions, expensemoneyportions, refundreturninnmoneyportions)
	income_currencies, expenses_currencies, totals_dict = calculate_net(income_currencies, expenses_currencies) #gets income payments by curency dictionary and expenses the returns 3rd dict of totals or profit/los for every currency
	
	# print("TOTALS")
	# print(totals_dict)

	cash_in_hand_print_out = ""
	total_value = 0
	keys = totals_dict.keys()
	for key in keys:
		sc = str(totals_dict[key][0])
		pa = locale.format_string('%.2f', float(totals_dict[key][1]), grouping=True)
		ra = locale.format_string('%.2f', float(totals_dict[key][2]), grouping=True)
		cash_in_hand_print_out += f"""\n{sc:<15}{pa:>10}{ra:>20}"""
		total_value += float(ra)


	text = ""

	text += f"""
Date:	{ filter_date }
By:	{ request.user.first_name.title() } { request.user.last_name.title() }

{'Sales Profit:'}     {locale.format_string('%.2f', float(sales_profit), grouping=True):>26}
{'Number of Sales:'}  {locale.format_string('%.2f', float(number_of_sales), grouping=True):>26}
{'Sales Value:'}      {locale.format_string('%.2f', float(sales_value), grouping=True):>26}
{'Expenses Value:'}   {locale.format_string('%.2f', float(expenses_value), grouping=True):>26}
{'Total Returns Inn:'}{locale.format_string('%.2f', float(total_returns_inn), grouping=True):>26}
{'Total Returns Out:'}{locale.format_string('%.2f', float(total_returns_out), grouping=True):>26}
{'Received Stock:'}   {locale.format_string('%.2f', float(received_stock), grouping=True):>26}
{'Total Profit:'}     {locale.format_string('%.2f', float(total_profit), grouping=True):>26}

CASH AT HAND
----------------------------------------------
{'CURR':<15}{'AMOUNT':>10}{'VALUE':>20}
{cash_in_hand_print_out}
----------------------------------------------
{'TOTAL'} {locale.format_string('%.2f', float(total_value), grouping=True):>39}
----------------------------------------------
"""
	print(text)
	custome_status, message = print_formated_text(text)
	return JsonResponse({"custome_status": custome_status, "message": message,})




# PERIODIC REPORTS


def print_data_for_year_end(request):
	filter_date = request.GET.get('filter_date')
	month = int(1)
	year = int(filter_date[:4])
	filter_date_from = datetime.date(year, month, 1)
	filter_date_to = datetime.date(year, 12, calendar.monthrange(year, month)[1])

	custome_status, message = print_time_frame_summary_to_pos_printer(request, filter_date, filter_date_from, filter_date_to)

	return JsonResponse({"custome_status": custome_status, "message": message,})



def print_data_for_month_end(request):
	filter_date = request.GET.get('filter_date')
	month = int(filter_date[5:])
	year = int(filter_date[:4])
	filter_date_from = datetime.date(year, month, 1)
	filter_date_to = datetime.date(year, month, calendar.monthrange(year, month)[1])

	custome_status, message = print_time_frame_summary_to_pos_printer(request, filter_date, filter_date_from, filter_date_to)

	return JsonResponse({"custome_status": custome_status, "message": message,})



def print_data_for_day_end(request):
	filter_date = request.GET.get('filter_date')
	filter_date_from = filter_date
	filter_date_to = filter_date


	custome_status, message = print_time_frame_summary_to_pos_printer(request, filter_date, filter_date_from, filter_date_to)

	return JsonResponse({"custome_status": custome_status, "message": message,})



def print_time_frame_summary_to_pos_printer(request, filter_date, filter_date_from, filter_date_to):
	summery, income_currencies, expenses_currencies, totals_dict = get_day_end_summary(filter_date_from, filter_date_to)

	cash_in_hand_print_out = ""

	total_rated_value_all_currencies = 0
	keys = totals_dict.keys()
	for key in keys:
		shortcut = str(totals_dict[key][0])
		income_amount = locale.format_string('%.2f', float(income_currencies[key][1]), grouping=True)
		expenses_amount = f"- {locale.format_string('%.2f', float(expenses_currencies[key][1]), grouping=True)}"
		total_amount = locale.format_string('%.2f', float(totals_dict[key][1]), grouping=True)
		total_value = locale.format_string('%.2f', float(totals_dict[key][2]), grouping=True)


		cash_in_hand_print_out += f"""{shortcut:<14}{income_amount:>15}{'':>16}
{'':<14}{expenses_amount:>15}{'':>16}
{'__________':>29}
{'':<14}{total_amount:>15}{total_value:>16}
----------------------------------------------
"""
		total_rated_value_all_currencies += float(total_value.replace(',', ''))

	text = f"""
		***************
		DAY-END SUMMERY
		***************
		FOR: { filter_date }


By:         { request.user.first_name.title() } { request.user.last_name.title() }
Printed at: { str(datetime_.today())[:16] }

SALES:
----------------------------------------------
{'Number of Sales'}        {locale.format_string('%.0f', summery['number_of_sales'], grouping=True):>22}
{'Items Sold'}             {locale.format_string('%.0f', summery['number_of_items_sold'], grouping=True):>22}
{'Cost of Items Sold'}     {locale.format_string('%.2f', summery['cost_of_sales'], grouping=True):>22}
{'Gross Sales Value'}      {locale.format_string('%.2f', summery['gross_sales_value'], grouping=True):>22}
{'Discounts Offered'}      {locale.format_string('%.2f', summery['discount_given'], grouping=True):>22}
{'Sales Value'}            {locale.format_string('%.2f', summery['sales_value'], grouping=True):>22}
{'Total Credit Notes'}     {locale.format_string('%.0f', summery['total_credit_notes'], grouping=True):>22}
{'Total Returns'}          {locale.format_string('%.0f', summery['total_returns_inn'], grouping=True):>22}
{'Total Items Returned'}   {locale.format_string('%.0f', summery['total_items_returned_inn'], grouping=True):>22}
    {'Returns Value'}      {locale.format_string('%.2f', summery['returns_inn_value'], grouping=True):>22}
    {'Refund Paid'}        {locale.format_string('%.2f', summery['refund_paid'], grouping=True):>22}
    {'Refund Outstanding'} {locale.format_string('%.2f', summery['refund_outstanding'], grouping=True):>22}
----------------------------------------------
{'Net Sales Value'}        {locale.format_string('%.2f', summery['net_sales_value'], grouping=True):>22}
----------------------------------------------
{'Sales Profit'}           {locale.format_string('%.2f', summery['sales_profit'], grouping=True):>22}
==============================================
	
INVOICES:
----------------------------------------------
{'Total Invoices Received'}{locale.format_string('%.0f', summery['total_invoices'], grouping=True):>22}
{'Total Items Received'}   {locale.format_string('%.0f', summery['total_items_received'], grouping=True):>22}
{'Received Stock Value'}   {locale.format_string('%.2f', summery['received_stock_value'], grouping=True):>22}
{'Discount Received'}      {locale.format_string('%.2f', summery['discount_received'], grouping=True):>22}
{'Invoice Payments Value'} {locale.format_string('%.2f', summery['paid_for_invoices'], grouping=True):>22}
{'Total Returns Out'}      {locale.format_string('%.0f', summery['total_returns_out'], grouping=True):>22}
{'Returns Out Refunds'}    {locale.format_string('%.2f', summery['returns_out_value'], grouping=True):>22}
{'Paid Return Out Refunds'}{locale.format_string('%.2f', summery['paid_returns_out_value'], grouping=True):>22}
==============================================

EXPENSES:
----------------------------------------------
{'Total Incurred Expenses'}{locale.format_string('%.0f', summery['total_expenses'], grouping=True):>22}
{'Incurred Expenses Value'}{locale.format_string('%.2f', summery['expenses_value'], grouping=True):>22}
{'Paid Expenses Value'}    {locale.format_string('%.2f', summery['paid_for_expenses'], grouping=True):>22}
==============================================

CASHFLOW SUMMERY:
----------------------------------------------
{'CASH INFLOW'}           {locale.format_string('%.2f', summery['cash_inflow'], grouping=True):>22}
{'CASH OUTFLOW'}          {locale.format_string('%.2f', summery['cash_outflow'], grouping=True):>22}
----------------------------------------------
{'CASHFOLW BALANCE'}      {locale.format_string('%.2f', summery['cash_flow_balance'], grouping=True):>22}
==============================================


CASHFLOW DEATAILS:
**********************************************
{'CURR':<14}{'AMOUNT':>15}{'VALUE':>16}
**********************************************
{cash_in_hand_print_out}
{'TOTAL CASH AT HAND'} {locale.format_string('%.2f', float(total_rated_value_all_currencies), grouping=True):>26}
______________________________________________
----------------------------------------------
	"""
    # {'Refund Agreed'}      {locale.format_string('%.2f', summery['refund_agreed'], grouping=True):>22}
    # {'Returns Allawances'} {locale.format_string('%.2f', summery['returns_inn_allowances'], grouping=True):>22}

	print(text)
	custome_status, message = print_formated_text(text)
	return custome_status, message




def get_data_for_year_end(request):
	filter_date = request.GET.get('filter_date')
	month = int(1)
	year = int(filter_date[:4])
	filter_date_from = datetime.date(year, month, 1)
	print("-------------------------")
	print(filter_date_from)
	filter_date_to = datetime.date(year, 12, calendar.monthrange(year, month)[1])
	print(filter_date_to)



	# get daily summeries
	summery, income_currencies, expenses_currencies, totals_dict = get_day_end_summary(filter_date_from, filter_date_to)

	summery_table = f"""
		<tr>
			<td>Number of Sales</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['number_of_sales'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Discount received</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['discount_received'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Sales Profit</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['sales_profit'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Sales Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['sales_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Expenses</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_expenses'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Discount Offered</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['discount_given'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Expenses Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['expenses_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Returns Inn</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_returns_inn'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Returns Inn Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['returns_inn_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Returns Out</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_returns_out'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Returns Out Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['returns_out_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Invoices Received</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_invoices'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Items Received</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_items_received'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Received Stock Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['received_stock_value'], grouping=True) }</td>
		</tr>
		<tr>
			<th>Total Profit</th>
			<th style="text-align:right;"><u>{ locale.format_string('%.2f', summery['total_profit'], grouping=True) }</u></th>
		</tr>
	"""

	cash_table = f"""
		<tr>
			<th>CURRENCY</th>
			<th style="text-align: right;">AMOUNT</th>
			<th style="text-align: right;">VALUE</th>
		</tr>
	"""

	if len(totals_dict.keys()) == 0:
		cash_table = f"""
		<tr>
			<td colspan=3 style="text-align: center;">No payments for this day</td>
		</tr>
		"""
	for key in totals_dict.keys():
		cash_table += f"""
	        <tr>
	            <td>{totals_dict[key][0]}</td>
	            <td style="text-align: right; color: blue;">{ locale.format_string('%.2f', float(income_currencies[key][1]), grouping=True) }</td>
	            <td></td>
	        </tr>
	        <tr>
	            <td></td>
	            <td style="text-align: right; color: red;">({ locale.format_string('%.2f', float(expenses_currencies[key][1]), grouping=True) })</td>
	            <td></td>
	        </tr>
	        <tr>
	            <td></td>
	            <td style="text-align: right;"><u>{ locale.format_string('%.2f', float(totals_dict[key][1]), grouping=True) }</u></td>
	            <td style="text-align: right;"><u>{ locale.format_string('%.2f', float(totals_dict[key][2]), grouping=True) }</u></td>
	        </tr>
	"""

	return JsonResponse({'summery_table':summery_table, 'cash_table': cash_table, 'custome_status': ""})





def get_data_for_month_end(request):
	filter_date = request.GET.get('filter_date')
	month = int(filter_date[5:])
	year = int(filter_date[:4])
	filter_date_from = datetime.date(year, month, 1)
	filter_date_to = datetime.date(year, month, calendar.monthrange(year, month)[1])


	# get daily summeries
	summery, income_currencies, expenses_currencies, totals_dict = get_day_end_summary(filter_date_from, filter_date_to)

	summery_table = f"""
		<tr>
			<td>Number of Sales</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['number_of_sales'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Discount received</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['discount_received'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Sales Profit</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['sales_profit'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Sales Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['sales_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Expenses</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_expenses'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Discount Offered</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['discount_given'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Expenses Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['expenses_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Returns Inn</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_returns_inn'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Returns Inn Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['returns_inn_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Returns Out</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_returns_out'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Returns Out Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['returns_out_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Invoices Received</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_invoices'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Items Received</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_items_received'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Received Stock Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['received_stock_value'], grouping=True) }</td>
		</tr>
		<tr>
			<th>Total Profit</th>
			<th style="text-align:right;"><u>{ locale.format_string('%.2f', summery['total_profit'], grouping=True) }</u></th>
		</tr>
	"""

	cash_table = f"""
		<tr>
			<th>CURRENCY</th>
			<th style="text-align: right;">AMOUNT</th>
			<th style="text-align: right;">VALUE</th>
		</tr>
	"""

	if len(totals_dict.keys()) == 0:
		cash_table = f"""
		<tr>
			<td colspan=3 style="text-align: center;">No payments for this day</td>
		</tr>
		"""
	for key in totals_dict.keys():
		cash_table += f"""
	        <tr>
	            <td>{totals_dict[key][0]}</td>
	            <td style="text-align: right; color: blue;">{ locale.format_string('%.2f', float(income_currencies[key][1]), grouping=True) }</td>
	            <td></td>
	        </tr>
	        <tr>
	            <td></td>
	            <td style="text-align: right; color: red;">({ locale.format_string('%.2f', float(expenses_currencies[key][1]), grouping=True) })</td>
	            <td></td>
	        </tr>
	        <tr>
	            <td></td>
	            <td style="text-align: right;"><u>{ locale.format_string('%.2f', float(totals_dict[key][1]), grouping=True) }</u></td>
	            <td style="text-align: right;"><u>{ locale.format_string('%.2f', float(totals_dict[key][2]), grouping=True) }</u></td>
	        </tr>
	"""

	return JsonResponse({'summery_table':summery_table, 'cash_table': cash_table, 'custome_status': ""})




def get_data_for_day_end(request):
	filter_date = request.GET.get('filter_date')
	filter_date_from = filter_date
	filter_date_to = filter_date


	# get daily summeries
	summery, income_currencies, expenses_currencies, totals_dict = get_day_end_summary(filter_date_from, filter_date_to)

	summery_table = f"""
		<tr>
			<td>Number of Sales</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['number_of_sales'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Discount Received</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['discount_received'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Sales Profit</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['sales_profit'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Sales Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['sales_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Expenses</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_expenses'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Discount Offered</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['discount_given'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Expenses Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['expenses_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Returns Inn</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_returns_inn'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Returns Inn Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['returns_inn_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Returns Out</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_returns_out'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Returns Out Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['returns_out_value'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Invoices Received</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_invoices'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Total Items Received</td>
			<td style="text-align:right;">{ locale.format_string('%.0f', summery['total_items_received'], grouping=True) }</td>
		</tr>
		<tr>
			<td>Received Stock Value</td>
			<td style="text-align:right;">{ locale.format_string('%.2f', summery['received_stock_value'], grouping=True) }</td>
		</tr>
		<tr>
			<th>Total Profit</th>
			<th style="text-align:right;"><u>{ locale.format_string('%.2f', summery['total_profit'], grouping=True) }</u></th>
		</tr>
	"""

	cash_table = f"""
		<tr>
			<th>CURRENCY</th>
			<th style="text-align: right;">AMOUNT</th>
			<th style="text-align: right;">VALUE</th>
		</tr>
	"""

	if len(totals_dict.keys()) == 0:
		cash_table = f"""
		<tr>
			<td colspan=3 style="text-align: center;">No payments for this day</td>
		</tr>
		"""
	for key in totals_dict.keys():
		cash_table += f"""
	        <tr>
	            <td>{totals_dict[key][0]}</td>
	            <td style="text-align: right; color: blue;">{ locale.format_string('%.2f', float(income_currencies[key][1]), grouping=True) }</td>
	            <td></td>
	        </tr>
	        <tr>
	            <td></td>
	            <td style="text-align: right; color: red;">({ locale.format_string('%.2f', float(expenses_currencies[key][1]), grouping=True) })</td>
	            <td></td>
	        </tr>
	        <tr>
	            <td></td>
	            <td style="text-align: right;"><u>{ locale.format_string('%.2f', float(totals_dict[key][1]), grouping=True) }</u></td>
	            <td style="text-align: right;"><u>{ locale.format_string('%.2f', float(totals_dict[key][2]), grouping=True) }</u></td>
	        </tr>
	"""

	return JsonResponse({'summery_table':summery_table, 'cash_table': cash_table, 'custome_status': ""})





#########################################################################################################
#	DATA SYNC
#########################################################################################################


def sync_data_for_day_end(request):
	filter_date = request.GET.get('filter_date')
	filter_date_from = filter_date
	filter_date_to = filter_date

	# get daily summeries
	summery, income_currencies, expenses_currencies, totals_dict = get_day_end_summary(filter_date_from, filter_date_to)

	cash_in_hand_print_out = ""

	total_rated_value_all_currencies = 0
	keys = totals_dict.keys()
	for key in keys:
		shortcut = str(totals_dict[key][0])
		income_amount = locale.format_string('%.2f', float(income_currencies[key][1]), grouping=True)
		expenses_amount = f"- {locale.format_string('%.2f', float(expenses_currencies[key][1]), grouping=True)}"
		total_amount = locale.format_string('%.2f', float(totals_dict[key][1]), grouping=True)
		total_value = locale.format_string('%.2f', float(totals_dict[key][2]), grouping=True)


	# creating a dict to post
	dict_data = {
		# identity
		'sync_type': 'Transactions Summery Report',
		'company_name': f'{ configuration.company_name }',
		'branch_id': f'{ configuration.branch_id }',
		'branch_verification_key': f'{ configuration.branch_verification_key }',
		'time_frame': 'Day',
		'date': f'{ filter_date }',
		'user_id': f'{ request.user.id }',
		'user_name_text': f'{ request.user.first_name.title() } { request.user.last_name.title() } ({ request.user.username.title() })',
		# data
		'number_of_sales': summery['number_of_sales'],
		'discount_received': summery['discount_received'],
		'sales_profit': summery['sales_profit'],
		'sales_value': summery['sales_value'],
		'total_expenses': summery['total_expenses'],
		'expenses_value': summery['expenses_value'],
		'discount_given': summery['discount_given'],
		'total_returns_inn': summery['total_returns_inn'],
		'returns_inn_value': summery['returns_inn_value'],
		'total_returns_out': summery['total_returns_out'],
		'returns_out_value': summery['returns_out_value'],
		'total_invoices': summery['total_invoices'],
		'total_items_received': summery['total_items_received'],
		'received_stock_value': summery['received_stock_value'],
		'total_profit': summery['total_profit'],
	}
	custome_status, message = sync(dict_data)

	return JsonResponse({"custome_status": custome_status, "message": message,})


def sync_data_for_month_end(request):
	filter_date = request.GET.get('filter_date')
	month = int(filter_date[5:])
	year = int(filter_date[:4])
	filter_date_from = datetime.date(year, month, 1)
	filter_date_to = datetime.date(year, month, calendar.monthrange(year, month)[1])

	# get daily summeries
	summery, income_currencies, expenses_currencies, totals_dict = get_day_end_summary(filter_date_from, filter_date_to)

	cash_in_hand_print_out = ""

	total_rated_value_all_currencies = 0
	keys = totals_dict.keys()
	for key in keys:
		shortcut = str(totals_dict[key][0])
		income_amount = locale.format_string('%.2f', float(income_currencies[key][1]), grouping=True)
		expenses_amount = f"- {locale.format_string('%.2f', float(expenses_currencies[key][1]), grouping=True)}"
		total_amount = locale.format_string('%.2f', float(totals_dict[key][1]), grouping=True)
		total_value = locale.format_string('%.2f', float(totals_dict[key][2]), grouping=True)
		total_value_clean = float(totals_dict[key][2])


	# creating a dict to post
	dict_data = {
		# identity
		'sync_type': 'Transactions Summery Report',
		'company_name': f'{ configuration.company_name }',
		'branch_id': f'{ configuration.branch_id }',
		'branch_verification_key': f'{ configuration.branch_verification_key }',
		'time_frame': 'Month',
		'date': f'{ filter_date }',
		'user_id': f'{ request.user.id }',
		'user_name_text': f'{ request.user.first_name.title() } { request.user.last_name.title() } ({ request.user.username.title() })',
		# data
		'number_of_sales': summery['number_of_sales'],
		'discount_received': summery['discount_received'],
		'sales_profit': summery['sales_profit'],
		'sales_value': summery['sales_value'],
		'total_expenses': summery['total_expenses'],
		'expenses_value': summery['expenses_value'],
		'discount_given': summery['discount_given'],
		'total_returns_inn': summery['total_returns_inn'],
		'returns_inn_value': summery['returns_inn_value'],
		'total_returns_out': summery['total_returns_out'],
		'returns_out_value': summery['returns_out_value'],
		'total_invoices': summery['total_invoices'],
		'total_items_received': summery['total_items_received'],
		'received_stock_value': summery['received_stock_value'],
		'total_profit': summery['total_profit'],
	}
	custome_status, message = sync(dict_data)

	return JsonResponse({"custome_status": custome_status, "message": message,})

# ------------------------------------
# def ...():
#   data = {}
#   for i in range(num_records):
#     record = {}
#     for j in range(num_fields):
#       field_name = f"field_{j}"
#       field_value = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(1, field_length)))
#       record[field_name] = field_value
#     data[f"record_{i}"] = record
#   return data
# ------------------------------------

def sync_current_stock_data(request):
	current_stock_data = Stock.objects.filter(status=True).order_by('product__title')
	data = {
		'sync_type': 'Current Stock Data',
		'company_name': f'{ configuration.company_name }',
		'branch_id': f'{ configuration.branch_id }',
		'branch_verification_key': f'{ configuration.branch_verification_key }',
		'user_id': f'{ request.user.id }',
		'user_name_text': f'{ request.user.first_name.title() } { request.user.last_name.title() } ({ request.user.username.title() })',
	}

	counter = 1
	for stock in current_stock_data:
		# print('--------------')
		product = {}
		product["product_code"] = f"{stock.product.product_code}"
		product["title"] = f"{stock.product.title}"
		product["total_units"] = f"{stock.total_units}"
		product["selling_price"] = f"{stock.selling_price}"
		data[f'{counter}'] = product
		counter += 1
	dict_data = data
	print(dict_data)
	custome_status, message = sync(dict_data)

	if custome_status == "":
		configuration.last_sync_user = f'{ request.user.first_name.title() } { request.user.last_name.title() } ({ request.user.username.title() })',
		configuration.save()
		configuration.last_sync_time = str(configuration.updated_at)[:16]
		configuration.save()

	last_sync_data = {
		"last_sync_time": configuration.last_sync_time,
		"last_sync_user": configuration.last_sync_user,
	}

	return JsonResponse({"custome_status": custome_status, "message": message, "last_sync_data": last_sync_data })



def sync_data_for_year_end(request):
	filter_date = request.GET.get('filter_date')
	month = int(1)
	year = int(filter_date[:4])
	filter_date_from = datetime.date(year, month, 1)
	filter_date_to = datetime.date(year, 12, calendar.monthrange(year, month)[1])

	# get daily summeries
	summery, income_currencies, expenses_currencies, totals_dict = get_day_end_summary(filter_date_from, filter_date_to)

	cash_in_hand_print_out = ""

	total_rated_value_all_currencies = 0
	keys = totals_dict.keys()
	for key in keys:
		shortcut = str(totals_dict[key][0])
		income_amount = locale.format_string('%.2f', float(income_currencies[key][1]), grouping=True)
		expenses_amount = f"({locale.format_string('%.2f', float(expenses_currencies[key][1]), grouping=True)})"
		total_amount = locale.format_string('%.2f', float(totals_dict[key][1]), grouping=True)
		total_value = locale.format_string('%.2f', float(totals_dict[key][2]), grouping=True)
		total_value_clean = float(totals_dict[key][2])


	# creating a dict to post
	dict_data = {
		# identity
		'sync_type': 'Transactions Summery Report',
		'company_name': f'{ configuration.company_name }',
		'branch_id': f'{ configuration.branch_id }',
		'branch_verification_key': f'{ configuration.branch_verification_key }',
		'time_frame': 'Year',
		'date': f'{ filter_date }',
		'user_id': f'{ request.user.id }',
		'user_name_text': f'{ request.user.first_name.title() } { request.user.last_name.title() } ({ request.user.username.title() })',
		# data
		'number_of_sales': summery['number_of_sales'],
		'discount_received': summery['discount_received'],
		'sales_profit': summery['sales_profit'],
		'sales_value': summery['sales_value'],
		'total_expenses': summery['total_expenses'],
		'expenses_value': summery['expenses_value'],
		'discount_given': summery['discount_given'],
		'total_returns_inn': summery['total_returns_inn'],
		'returns_inn_value': summery['returns_inn_value'],
		'total_returns_out': summery['total_returns_out'],
		'returns_out_value': summery['returns_out_value'],
		'total_invoices': summery['total_invoices'],
		'total_items_received': summery['total_items_received'],
		'received_stock_value': summery['received_stock_value'],
		'total_profit': summery['total_profit'],
	}
	custome_status, message = sync(dict_data)

	return JsonResponse({"custome_status": custome_status, "message": message,})




#########################################################################################################
#	DATA SYNC
#########################################################################################################


#########################################################################################################
#	DATA BACKUP
#########################################################################################################

def create_backup(request):
	from django.http import FileResponse
	return FileResponse(open('db.sqlite3', 'rb'))

#########################################################################################################
#	DATA BACKUP
#########################################################################################################



# fixes


def update_reorder_quanties_to(request, pk):
	new_reorder_quantity = int(pk)
	stocks = Stock.objects.all()

	count = 0
	for stock in stocks:
		count += 1
		print(count)
		print(f"""ID: { stock.id }\t({ stock.product.product_code }) { stock.product.title }, { stock.product.details }""")
		print(f"""REORDER QUANTITY: { stock.reorder_quantity }, QUANTITY: { stock.total_units }""")
		stock.reorder_quantity = new_reorder_quantity
		stock.save()

		print(f"""CHANGED TO: \n \tREORDER QUANTITY: { stock.reorder_quantity }, QUANTITY: { stock.total_units }""")

		print(f"""\t✅✅✅\n""")
	print(f"DONE: { count } records affected! ✅✅✅")


	return JsonResponse({"Total affected: ": count})



# runs automaticaly to fight a batch deactivating bug
# it shoul be called in stockpage and baches page
def activate_all_deactivated_batches(request):
	batches = Batch.objects.filter(total_units__gt=0, status=False)
	for batch in batches:
		batch.status = True
		batch.save()

	print(f"{batches.count()} activated")


@transaction.atomic
def db_fix(request):
	import csv

	global_suplier = Supplier()
	global_suplier.company_name = "INTIAL DEFAULT"
	global_suplier.registration_number = "INTIAL DEFAULT"
	global_suplier.phone_number = ""
	global_suplier.email = ""
	global_suplier.address = ""
	global_suplier.created_by = request.user
	global_suplier.save()
	print("global_suplier saved")

	global_manufacturer = Manufacturer()
	global_manufacturer.company_name = "INTIAL DEFAULT"
	global_manufacturer.registration_number = "INTIAL DEFAULT"
	global_manufacturer.phone_number = ""
	global_manufacturer.email = ""
	global_manufacturer.address = ""
	global_manufacturer.created_by = request.user
	global_manufacturer.save()
	print("global_manufacturer saved")

	global_invoice = Invoice()
	global_invoice.invoice_number = "AAAA0001"
	global_invoice.supplier = global_suplier
	global_invoice.date = datetime_.today().date()
	global_invoice.created_by = request.user
	global_invoice.save()
	print("global_invoice saved")

	global_vat_code = VATCode()
	global_vat_code.title = "Zero rated"
	global_vat_code.percentage = 0
	global_vat_code.created_by = request.user
	global_vat_code.save()
	print("global_vat_code saved")

	counter = 0

	file_path = "reports/products.csv"
	with open(file_path, 'r', encoding='utf-8') as file:
		reader = csv.DictReader(file)
		for row in reader:
			counter+= 1
			new_product = Product()
			new_product.title = row['Name']
			new_product.bar_code = row['Barcode']
			# new_product.product_code = row['']
			new_product.details = row['Name']
			new_product.vat_code = global_vat_code
			new_product.created_by = request.user
			new_product.save()
			print("new_product saved")

			new_stock = Stock()
			new_stock.product = new_product
			new_stock.selling_price = row['Price']
			new_stock.markup = row['Markup']
			new_stock.reorder_quantity = 5
			# new_stock.expiration_warning_days = row['']
			# new_stock.status = row['']
			# new_stock.is_tax_inclusive = row['']
			new_stock.save()
			print("new_stock saved")


			new_batch = Batch()
			new_batch.batch_number = f"INTIAL-B-{counter}"
			new_batch.stock = new_stock
			new_batch.manufacturer = global_manufacturer
			new_batch.invoice = global_invoice
			# new_batch.total_packs = row['Quantity']
			new_batch.total_packs = 1
			new_batch.pack_size = 1
			# new_batch.total_units = row['Quantity']
			new_batch.total_units = 1
			new_batch.buying_pack_price = row['Cost']
			new_batch.VAT = 0
			new_batch.markup = row['Markup']
			new_batch.created_by = request.user
			new_batch.save()
			print(f"{counter} new_batch saved")	
	return JsonResponse({"response":"Done"})









def quick_print_test(request):
    """Simplest working version"""
    import win32ui
    from PIL import Image, ImageWin
    
    printer_name = "POS-90"
    
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    
    hDC.StartDoc("Test")
    hDC.StartPage()
    
    # Print text
    font = win32ui.CreateFont({"name": "Arial", "height": 200})
    hDC.SelectObject(font)
    hDC.TextOut(100, 100, "Hello World")
    hDC.TextOut(100, 300, "Line 2")
    hDC.TextOut(100, 500, "Line 3")
    
    # Print image
    img = Image.open("logo.png")
    dib = ImageWin.Dib(img)
    PHYSICALWIDTH = 110
    printer_width = hDC.GetDeviceCaps(PHYSICALWIDTH)
    dib.draw(hDC.GetHandleOutput(), (100, 700, printer_width - 100, 1000))
    
    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()
    
    return JsonResponse({"response": "Job sent"})