from payments.models import SaleTransaction, Sale, Expense, Payment
from enventory.models import ReturnOut, ReturnInn, Invoice, CreditNote

from reusable_functions.univesal.reporting import group_money_portions_into_dict
from reusable_functions.univesal.reporting import calculate_net

from django.db.models import Sum, F


def get_day_end_summary(filter_date_from, filter_date_to):
	number_of_sales = 0
	number_of_items_sold = 0
	gross_sales_value = 0
	discount_given = 0
	sales_value = 0
	net_sales_value = 0
	returns_inn_value = 0
	refund_agreed = 0
	refund_paid = 0
	refund_outstanding = 0
	cost_of_sales = 0
	sales_profit = 0
	returns_inn_allowances = 0
	returns_out_value = 0
	paid_returns_out_value = 0

	total_credit_notes = 0
	total_returns_inn = 0
	total_items_returned_inn = 0




	gross_sales = 0
	net_sales = 0
	total_expenses = 0
	expenses_value = 0
	total_returns_inn = 0
	total_returns_out = 0
	total_invoices = 0
	total_items_received = 0
	received_stock_value = 0
	total_profit = 0
	discount_received = 0
	paid_for_invoices = 0
	paid_for_expenses = 0

	total_income = 0
	total_expense = 0

	cash_inflow = 0
	cash_outflow = 0



	# invoice_payments = InvoiceMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to))
	invoice_payments = Payment.objects.filter(payment_for="INVOICE", date__date__range=(filter_date_from, filter_date_to))
	for invoice_payment in invoice_payments:
		paid_for_invoices += invoice_payment.rated_value

	# expense_payments = ExpenseMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to))
	expense_payments = Payment.objects.filter(payment_for="EXPENSE", date__date__range=(filter_date_from, filter_date_to))
	for expense_payment in expense_payments:
		paid_for_expenses += expense_payment.rated_value


	returns_out_refund_payments = Payment.objects.filter(payment_for="RETURN_OUT_REFUND", date__date__range=(filter_date_from, filter_date_to))
	for refund in returns_out_refund_payments:
		paid_returns_out_value += refund.rated_value


	sale_transactions = SaleTransaction.objects.filter(created_at__date__range=(filter_date_from, filter_date_to))
	number_of_sales = sale_transactions.count()
	for sale_transaction in sale_transactions:
		discount_given += float(sale_transaction.discount)

	sales = Sale.objects.filter(created_at__date__range=(filter_date_from, filter_date_to))
	for sale in sales:
		number_of_items_sold += float(sale.actual_sales)
		sales_profit += float(sale.profit) 
		gross_sales_value += float(sale.selling_price)
		cost_of_sales += sale.buying_unit_price * sale.quantity


	expenses = Expense.objects.filter(date__date__range=(filter_date_from, filter_date_to))
	total_expenses = expenses.count()
	for expense in expenses:
		expenses_value += float(expense.price)

	returns_inn = ReturnInn.objects.filter(created_at__date__range=(filter_date_from, filter_date_to))
	total_returns_inn = returns_inn.count()

	for return_inn in returns_inn:
		returns_inn_value += float(return_inn.sale_value)
		total_items_returned_inn += return_inn.total_units


	credit_notes = CreditNote.objects.filter(created_at__date__range=(filter_date_from, filter_date_to))
	total_credit_notes = credit_notes.count()
	for credit_note in credit_notes:
		refund_agreed += float(credit_note.refund_amount)



	returns_out = ReturnOut.objects.filter(created_at__date__range=(filter_date_from, filter_date_to))
	total_returns_out = returns_out.count()
	for return_out in returns_out:
		returns_out_value += float(return_out.refund_amount)



	invoices = Invoice.objects.filter(created_at__date__range=(filter_date_from, filter_date_to))
	total_invoices = invoices.count()
	for invoice in invoices:
		total_items_received += float(invoice.total_items)
		received_stock_value += float(invoice.total_cost)
		discount_received += float(invoice.discount)


	sales_value = gross_sales_value - discount_given
	net_sales_value = sales_value - returns_inn_value



	# receiptmoneyportion = ReceiptMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to)).aggregate(x=Sum(F('amount_paid') / F('rate')))
	receiptmoneyportion = Payment.objects.filter(payment_for="RECEIPT", date__date__range=(filter_date_from, filter_date_to)).aggregate(x=Sum(F('amount_paid') / F('rate')))
	receiptmoneyportions_value = round(float(receiptmoneyportion['x']), 2) if receiptmoneyportion['x'] else 0
	
	# invoicemoneyportion = InvoiceMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to)).aggregate(x=Sum(F('amount_paid') / F('rate')))
	invoicemoneyportion = Payment.objects.filter(payment_for="INVOICE", date__date__range=(filter_date_from, filter_date_to)).aggregate(x=Sum(F('amount_paid') / F('rate')))
	invoicemoneyportions_value = round(float(invoicemoneyportion['x']), 2) if invoicemoneyportion['x'] else 0
	
	# expensemoneyportion = ExpenseMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to)).aggregate(x=Sum(F('amount_paid') / F('rate')))
	expensemoneyportion = Payment.objects.filter(payment_for="EXPENSE", date__date__range=(filter_date_from, filter_date_to)).aggregate(x=Sum(F('amount_paid') / F('rate')))
	expensemoneyportions_value = round(float(expensemoneyportion['x']), 2) if expensemoneyportion['x'] else 0

	# refundreturnoutmoneyportion = RefundReturnOutMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to)).aggregate(x=Sum(F('amount_paid') / F('rate')))
	refundreturnoutmoneyportion = Payment.objects.filter(payment_for="RETURN_OUT_REFUND", date__date__range=(filter_date_from, filter_date_to)).aggregate(x=Sum(F('amount_paid') / F('rate')))
	refundreturnoutmoneyportions_value = round(float(refundreturnoutmoneyportion['x']), 2) if refundreturnoutmoneyportion['x'] else 0

	# refundreturninnmoneyportion = RefundReturnInnMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to)).aggregate(x=Sum(F('amount_paid') / F('rate')))
	refundreturninnmoneyportion = Payment.objects.filter(payment_for="CREDIT_NOTE", date__date__range=(filter_date_from, filter_date_to)).aggregate(x=Sum(F('amount_paid') / F('rate')))
	refundreturninnmoneyportions_value = round(float(refundreturninnmoneyportion['x']), 2) if refundreturninnmoneyportion['x'] else 0

	refund_paid = refundreturninnmoneyportions_value

	refund_outstanding = refund_agreed - refund_paid
	returns_inn_allowances = returns_inn_value - refund_agreed

	cash_inflow = receiptmoneyportions_value + refundreturnoutmoneyportions_value
	cash_outflow = invoicemoneyportions_value + expensemoneyportions_value + refundreturninnmoneyportions_value
	cash_flow_balance = cash_inflow - cash_outflow

	total_profit = (sales_profit + returns_out_value + discount_given) - (expenses_value + received_stock_value + discount_given)

	total_profit = (sales_profit + discount_received) - (expenses_value)


	summery = {
		'number_of_sales': number_of_sales,
		'number_of_items_sold': number_of_items_sold,
		'gross_sales_value': gross_sales_value,
		'discount_given': discount_given,
		'sales_value': sales_value,
		'returns_inn_value': returns_inn_value,
		'total_returns_inn': total_returns_inn,
		'refund_agreed': refund_agreed,
		'refund_paid': refund_paid,
		'refund_outstanding': refund_outstanding,
		'cost_of_sales': cost_of_sales,
		'sales_profit': sales_profit,
		'returns_inn_allowances': returns_inn_allowances,
		'net_sales_value': net_sales_value,
		'total_credit_notes': total_credit_notes,
		'total_items_returned_inn': total_items_returned_inn,
		'paid_returns_out_value': paid_returns_out_value,



		'sales_value': sales_value,
		'total_expenses': total_expenses,
		'expenses_value': expenses_value,
		'total_returns_out': total_returns_out,
		'returns_out_value': returns_out_value,
		'total_invoices': total_invoices,
		'total_items_received': total_items_received,
		'received_stock_value': received_stock_value,
		'paid_for_invoices': paid_for_invoices,
		'total_profit': total_profit,
		'discount_received': discount_received,
		'paid_for_expenses': paid_for_expenses,
		'total_income': total_income,
		'total_expenses': total_expenses,
		'cash_inflow': cash_inflow,
		'cash_outflow': cash_outflow,
		'cash_flow_balance': cash_flow_balance,
	}

	# receiptmoneyportions = ReceiptMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to))
	receiptmoneyportions = Payment.objects.filter(payment_for="RECEIPT", date__date__range=(filter_date_from, filter_date_to))
	# refundreturnoutmoneyportions = RefundReturnOutMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to))
	refundreturnoutmoneyportions = Payment.objects.filter(payment_for="RETURN_OUT_REFUND", date__date__range=(filter_date_from, filter_date_to))
	# invoicemoneyportion = InvoiceMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to)).aggregate(x=Sum(F('amount_paid') / F('rate')))
	invoicemoneyportions = Payment.objects.filter(payment_for="INVOICE", date__date__range=(filter_date_from, filter_date_to))
	# expensemoneyportions = ExpenseMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to))
	expensemoneyportions = Payment.objects.filter(payment_for="EXPENSE", date__date__range=(filter_date_from, filter_date_to))
	# refundreturninnmoneyportions = RefundReturnInnMoneyPortion.objects.filter(date__date__range=(filter_date_from, filter_date_to))
	refundreturninnmoneyportions = Payment.objects.filter(payment_for="CREDIT_NOTE", date__date__range=(filter_date_from, filter_date_to))
	income_currencies, expenses_currencies = group_money_portions_into_dict(receiptmoneyportions, refundreturnoutmoneyportions, invoicemoneyportions, expensemoneyportions, refundreturninnmoneyportions)
	income_currencies, expenses_currencies, totals_dict = calculate_net(income_currencies, expenses_currencies) #gets income payments by curency dictionary and expenses the returns 3rd dict of totals or profit/los for every currency
	return summery, income_currencies, expenses_currencies, totals_dict


def get_daily_cash_summery(filter_date_from, filter_date_to):
	
	return 0