from django.conf import settings
from django.db import models
from django.utils import timezone

from django.http import HttpResponseRedirect

from accounts.models import ClientSetting, User, Branch


'''
CLASSES HERE
	VATCode
	PaymentMethod
	Payment
	SaleTransaction
	Sale
	ExpensesType
	Expense
'''



class VATCode(models.Model):
	global_id = models.UUIDField(unique=True, null=True, blank=True)
	version = models.IntegerField(default=1)
	needs_sync = models.BooleanField(default=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='created_%(class)s_records', null=True, blank=True)
	updated_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='updated_%(class)s_records', null=True, blank=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	
	title = models.CharField(max_length=30, blank=True, null=True)
	percentage = models.DecimalField(max_digits=22, decimal_places=4, default=0)
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True,blank=True, null=True)
	updated_at = models.DateTimeField(auto_now=True,blank=True, null=True)
	deleted = models.BooleanField(default=False)

	def __str__(self):
		return f'VAT Code {self.title}. {self.percentage}%'


class PaymentMethod(models.Model):
	global_id = models.UUIDField(unique=True, null=True, blank=True)
	version = models.IntegerField(default=1)
	needs_sync = models.BooleanField(default=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='created_%(class)s_records', null=True, blank=True)
	updated_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='updated_%(class)s_records', null=True, blank=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	
	currency = models.CharField(max_length=100)
	shortcut = models.CharField(max_length=10)
	rate = models.DecimalField(max_digits=15,decimal_places=2)
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	status = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)

	def __str__(self):
		return f' USD 1 : { self.rate }: { self.shortcut }'


class Payment(models.Model):
	global_id = models.UUIDField(unique=True, null=True, blank=True)
	version = models.IntegerField(default=1)
	needs_sync = models.BooleanField(default=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='created_%(class)s_records', null=True, blank=True)
	updated_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='updated_%(class)s_records', null=True, blank=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	
	amount_paid = models.DecimalField(max_digits=22,decimal_places=4)
	rate = models.DecimalField(max_digits=15,decimal_places=2)
	date = models.DateTimeField()
	payment_method = models.ForeignKey(PaymentMethod, on_delete=models.DO_NOTHING)
	
	payment_for = models.CharField(max_length=50, blank=True, null=True, default='') #RECEIPT, INVOICE, EXPENSE, RETURN_OUT_REFUND, CREDIT_NOTE
	payment_for_id = models.DecimalField(max_digits=15,decimal_places=0) #id for a selected type eg: ServiceRendered.id
	loose_status = models.BooleanField(default=False) #only true when a paying for a recipt, befor a sale is created

	change = models.DecimalField(max_digits=22,decimal_places=4, default=0 ) 
	change_given = models.DecimalField(max_digits=22,decimal_places=4, default=0)
	notes = models.TextField(max_length=255, blank=True, null=True, default='')

	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)

	def rated_value(self):
		return self.amount_paid / self.rate

	rated_value = property(rated_value)
	

# also called receipt
class SaleTransaction(models.Model):
	global_id = models.UUIDField(unique=True, null=True, blank=True)
	version = models.IntegerField(default=1)
	needs_sync = models.BooleanField(default=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='created_%(class)s_records', null=True, blank=True)
	updated_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='updated_%(class)s_records', null=True, blank=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	
	recipt_number = models.AutoField(primary_key=True)
	change = models.DecimalField(max_digits=22,decimal_places=4, default=0 ) 
	change_given = models.DecimalField(max_digits=22,decimal_places=4, default=0)
	discount = models.DecimalField(max_digits=22,decimal_places=4, default=0)
	
	buyer_name = models.CharField(max_length=100, default="")
	buyer_tin = models.CharField(max_length=100, default="")
	buyer_vat = models.CharField(max_length=100, default="")
	buyer_address = models.CharField(max_length=100, default="")
	buyer_tel = models.CharField(max_length=100, default="")

	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)
	open_state = models.BooleanField(default=True)



	def ultimate_recipt_number(self):
		try:
			configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
		except Exception as e:
			HttpResponseRedirect('client_settings_page')
			
		a = str(self.recipt_number).zfill(6)
		b = str(configuration.invoice_number_prefix)
		return b + a

	ultimate_recipt_number = property(ultimate_recipt_number)


	def totals(self):
		sales = Sale.objects.filter(sale_transaction=self.recipt_number)
		# receipt_money_portions = ReceiptMoneyPortion.objects.filter(sale_transaction=self.recipt_number)
		receipt_money_portions = Payment.objects.filter(payment_for="RECEIPT", payment_for_id=self.recipt_number)
		subtotal = 0
		VAT = 0
		total_cost = 0
		total_returned = 0
		profit = 0 - float(self.discount)
		for sale in sales:
			# if sale.total_price is not None:  # Check for None before conversion
			subtotal += float(sale.unit_price * sale.quantity)
			VAT += float(sale.VAT)
			profit += float(sale.profit)
			total_returned += sale.total_returned

		total_cost += subtotal + VAT

		paid_value = 0
		change_left = 0
		for money_portion in receipt_money_portions:
			paid_value += float(money_portion.rated_value)
			change_left += money_portion.change - money_portion.change_given


		totals = {
			'subtotal': subtotal,
			'VAT': VAT,
			'total_cost': total_cost,
			'paid_value': paid_value,
			'change_left': change_left,
			'profit': profit,
			'total_returned': total_returned,
		}
		return totals

	totals = property(totals)



class Sale(models.Model):
	global_id = models.UUIDField(unique=True, null=True, blank=True)
	version = models.IntegerField(default=1)
	needs_sync = models.BooleanField(default=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='created_%(class)s_records', null=True, blank=True)
	updated_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='updated_%(class)s_records', null=True, blank=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	
	sale_transaction = models.ForeignKey(SaleTransaction, on_delete=models.DO_NOTHING, blank=True, null=True)
	stock = models.ForeignKey('enventory.Stock', on_delete=models.DO_NOTHING)
	selling_price = models.DecimalField(max_digits=22,decimal_places=4) #its the salling price for the whole sale not for a single item
	VAT = models.DecimalField(max_digits=22,decimal_places=4)
	unit_price = models.DecimalField(max_digits=22,decimal_places=4)
	buying_unit_price = models.DecimalField(max_digits=22,decimal_places=4, default=0)
	total_returned = models.IntegerField(default=0)
	quantity = models.IntegerField()
	used_batches = models.CharField(max_length=3000, default='', null=True, blank=True)
	used_batch_quantities = models.CharField(max_length=3000, default='', null=True, blank=True)
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)

	def actual_sales(self):
		actual_sales = self.quantity - self.total_returned
		return round(actual_sales, 0)

	actual_sales = property(actual_sales)


	def total_price_before_return(self):
		total_price_before_return = (float(self.unit_price) * float(self.quantity )) + float(self.VAT)
		return total_price_before_return

	total_price_before_return = property(total_price_before_return)


	def total_price(self):
		"""Price after returns (including proportional VAT)"""
		kept = float(self.quantity) - float(self.total_returned)
		if float(self.quantity) == 0 or kept == 0:
			return float('0.00')
		
		subtotal_excl_vat = float(self.unit_price) * kept
		vat_on_kept = float(self.VAT) * (float(kept) / float(float(self.quantity)))
		return subtotal_excl_vat + vat_on_kept

	total_price = property(total_price)

	def profit(self):
		real_quantity = self.quantity - self.total_returned
		profit = (self.unit_price * real_quantity) - (self.buying_unit_price * real_quantity)
		return profit

	profit = property(profit)



class ExpensesType(models.Model):
	global_id = models.UUIDField(unique=True, null=True, blank=True)
	version = models.IntegerField(default=1)
	needs_sync = models.BooleanField(default=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='created_%(class)s_records', null=True, blank=True)
	updated_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='updated_%(class)s_records', null=True, blank=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	
	title = models.CharField(max_length=30)
	description = models.CharField(max_length=255, blank=True, null=True)
	active = models.BooleanField(default=True)
	default_price = models.DecimalField(max_digits=22,decimal_places=4, default=0, blank=True, null=True)

	reoccurring = models.BooleanField(default=False)
	reoccurring_interval = models.CharField(max_length=30, default="NONE") #DAILY, WEEKLY, MONTHLY, ANUALY

	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	deleted = models.BooleanField(default=False)

	def billing_method_d(self):
		if self.reoccurring == True:
			return "Automated"
		else:
			return "Manual"

	billing_method_d = property(billing_method_d)

	def reoccurring_interval_d(self):
		if self.reoccurring == True:
			return self.reoccurring_interval.title()
		else:
			return ""

	reoccurring_interval_d = property(reoccurring_interval_d)

	def __str__(self):
		return f'{ self.title } '


class Expense(models.Model):
	global_id = models.UUIDField(unique=True, null=True, blank=True)
	version = models.IntegerField(default=1)
	needs_sync = models.BooleanField(default=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='created_%(class)s_records', null=True, blank=True)
	updated_by_branch = models.ForeignKey(Branch, on_delete=models.DO_NOTHING, related_name='updated_%(class)s_records', null=True, blank=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	
	expense_type = models.ForeignKey(ExpensesType, on_delete=models.CASCADE)
	description = models.CharField(max_length=255, blank=True, null=True)
	date = models.DateTimeField()
	price = models.DecimalField(max_digits=22,decimal_places=4, blank=True, null=True)
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	deleted = models.BooleanField(default=False)


	def amount_paid(self):
		amount_paid = 0
		# money_portions = ExpenseMoneyPortion.objects.filter(expense=self.id)
		money_portions = Payment.objects.filter(payment_for="EXPENSE", payment_for_id=self.id)
		for money_portion in money_portions:
			amount_paid = float(amount_paid) + float(money_portion.rated_value)
		return amount_paid

	amount_paid = property(amount_paid)


	def status(self):
		status = float(self.price) - float(self.amount_paid)
		if status > 0:
			status = "BALANCE"
		elif status == 0:
			status = "CLEARED"
		elif status < 0:
			status = "CHANGE"
		return status

	status = property(status)


	def balance(self):
		balance = round(float(self.price) - float(self.amount_paid), 2)
		return balance

	balance = property(balance)


	def __str__(self):
		return f'{ self.expense_type.title } { self.price }'