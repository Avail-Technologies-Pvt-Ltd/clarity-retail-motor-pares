from django.db import models

from accounts.models import Supplier, Manufacturer, User, ClientSetting
from payments.models import VATCode, Payment

from django.http import HttpResponseRedirect



from datetime import datetime, date, timedelta


'''
CLASSES HERE:
	Product
	Stock
	Notification
	Batch
	BatchAdjustment
	BatchAdjustmentReason
	TemporaryInvoice
	Invoice
	InvoiceItem
	TemporaryInvoiceItem
	ReturnOut
	CreditNote
	ReturnInn
	ReturnReason
	Lable
'''



class Product(models.Model):
	bar_code = models.CharField(max_length=30, default='N/A', blank=True, null=True)
	title = models.CharField(max_length=30)
	product_code = models.CharField(max_length=50, default='N/A', blank=True, null=True)
	details = models.TextField(max_length=400, default='')
	vat_code = models.ForeignKey(VATCode, on_delete=models.DO_NOTHING, blank=True, null=True)

	created_by = models.CharField(max_length=30,blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	status = models.BooleanField(default=True)
	deleted = models.BooleanField(default=False)

	def __str__(self):
		return f'{self.title} {self.details}'

	
class Stock(models.Model):
	product = models.ForeignKey(Product, on_delete=models.DO_NOTHING)
	selling_price = models.DecimalField(max_digits=22, decimal_places=4, default='0')
	markup = models.DecimalField(max_digits=22, decimal_places=2, default=50, blank=True, null=True)
	reorder_quantity = models.IntegerField(default=5, blank=True, null=True)
	expiration_warning_days = models.IntegerField(default=90)
	status = models.BooleanField(default=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)

	def avarage_unit_cost(self):
		batchies = Batch.objects.filter(stock=self.id)
		combined_unit_price = 0
		combined_units = 0
		for batch in batchies:
			if batch.expiried == False:
				buying_unit_price = batch.buying_pack_price / batch.pack_size
				combined_unit_price += batch.total_units * buying_unit_price
				combined_units += batch.total_units
		try:
			avarage_unit_cost = combined_unit_price / combined_units
		except:
			avarage_unit_cost = 0

		return avarage_unit_cost

	avarage_unit_cost = property(avarage_unit_cost)

	def total_units(self):
		batchies = Batch.objects.filter(stock=self.id, status=True)
		total_units = 0
		for b in batchies:
			if b.expiried == False:
				total_units += b.total_units
		return total_units


	total_units = property(total_units)

	def stock_value(self):
		batchies = Batch.objects.filter(stock=self.id,  deleted=False, status=True)
		total_units = 0
		total_price = 0
		for b in batchies:
			if b.expiried == False:
				total_units += b.total_units

		return total_units * self.avarage_unit_cost

	stock_value = property(stock_value)


	def reorder_flag(self):
		reorder_flag = float(self.total_units) - float(self.reorder_quantity) 
		if reorder_flag <= 0:
			reorder_flag = True
		else:
			reorder_flag = False

		return reorder_flag

	reorder_flag = property(reorder_flag)


	def to_reorder(self):
		if self.total_units <= self.reorder_quantity:
			return f'{self.total_units} left.'
		else:
			return f'Still Enough'

	to_reorder = property(to_reorder)

	def __str__(self):
		return f' [{self.product.product_code}] { self.product.title }' #keep it this way unless you have a plan for lable in despensory

		

class Notification(models.Model):
	header = models.CharField(max_length=40)
	notification_type = models.CharField(max_length=30, default="") #expiring, expired, reorder
	detail = models.CharField(max_length=100)
	status = models.CharField(max_length=40, default="New") #Viewed
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)



class Batch(models.Model):
	batch_number = models.CharField(max_length=100)
	stock = models.ForeignKey(Stock, on_delete=models.DO_NOTHING)
	manufacturer = models.ForeignKey(Manufacturer, on_delete=models.DO_NOTHING)
	invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE)
	total_packs = models.IntegerField(blank=True, null=True)
	pack_size = models.IntegerField(blank=True, null=True)
	total_units = models.IntegerField(blank=True, null=True)
	buying_pack_price = models.DecimalField(max_digits=22,decimal_places=4, blank=True, null=True)
	VAT = models.DecimalField(max_digits=22,decimal_places=4, blank=True, null=True)
	markup = models.DecimalField(max_digits=22,decimal_places=4, blank=True, null=True)
	expiration_date = models.DateTimeField(blank=True, null=True)
	status = models.BooleanField(default=True)
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)

	def batch_value(self):
		batch_value = self.stock.selling_price * self.total_units
		return batch_value

	batch_value = property(batch_value)

	def total_units_available(self):
		total_units_available = self.total_units
		return total_units_available

	total_units_available = property(total_units_available)

	def total_units_bought(self):
		total_units_bought = self.total_packs * self.pack_size
		return total_units_bought

	total_units_bought = property(total_units_bought)



	def buying_unit_price(self):
		buying_unit_price = self.buying_pack_price / self.pack_size
		return buying_unit_price

	buying_unit_price = property(buying_unit_price)



	def buying_price(self):
		buying_price = (self.buying_unit_price * self.total_units_bought) + self.VAT
		return buying_price

	buying_price = property(buying_price)
	

	def expiration_days_left(self):
		expiration_days_left = self.expiration_date.date() - datetime.today().date()
		return expiration_days_left

	expiration_days_left = property(expiration_days_left)



	def expiring_in(self):
		txt = str(self.expiration_date.date() - (datetime.today().date()))
		if txt[0] == "-":
			txt = f'Expired { txt[1:][:-9] } ago'
		else:
			txt = f'Expiring in { txt[:-9] }'

		expiring_in = txt

		return expiring_in

	expiring_in = property(expiring_in)




	def expiried(self):
		try:
			expiried = self.expiration_date.date() <= (datetime.today().date())
		except:
			expiried = False
		return expiried

	expiried = property(expiried)




	def expiring(self):
		return (self.expiration_date.date() - timedelta(days=self.stock.expiration_warning_days)) < (datetime.today().date())#[:-13]

	expiring = property(expiring)



	def __str__(self):
		return f'{self.total_units}' #{self.product}' if this is uncommended, test will fail, i dont know why




class BatchAdjustmentReason(models.Model):
	shortcut = models.CharField(max_length=20)
	details = models.CharField(max_length=40)
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)
	status = models.BooleanField(default=True)


class BatchAdjustment(models.Model):
	batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
	action = models.CharField(max_length=10, default='Subtract')
	reason = models.ForeignKey(BatchAdjustmentReason, on_delete=models.DO_NOTHING)
	total_units = models.IntegerField()
	date = models.DateTimeField()
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)
	

class TemporaryInvoice(models.Model):
	invoice_number = models.CharField(max_length=40)
	supplier = models.ForeignKey(Supplier, on_delete=models.DO_NOTHING)
	discount = models.DecimalField(max_digits=22, decimal_places=2, default=0)
	date = models.DateTimeField()
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)

	def subtotal(self):
		items = TemporaryInvoiceItem.objects.all()#filter(invoice=self.id)
		subtotal = 0
		for item in items:
			subtotal += item.buying_pack_price * item.total_packs
		return subtotal

	subtotal = property(subtotal)

	def VAT_Value(self):
		VAT_Value = 0
		items = TemporaryInvoiceItem.objects.filter(invoice=self.id)
		for item in items:
			VAT_Value += item.vat_price
		return VAT_Value

	VAT_Value = property(VAT_Value)

	def total_amount(self):
		total_amount = 0
		items = TemporaryInvoiceItem.objects.filter(invoice=self.id)
		for item in items:
			total_amount += item.total_buying_pack_price
		return total_amount 

	def total_discount(self):
		total_discount = 0
		items = TemporaryInvoiceItem.objects.filter(invoice=self.id)
		for item in items:
			total_discount += item.discount_price

		return total_discount

	total_discount = property(total_discount)


	def __str__(self):
		return f'Invoice: {self.invoice_number}'


class Invoice(models.Model):
	invoice_number = models.CharField(max_length=40)
	supplier = models.ForeignKey(Supplier, on_delete=models.DO_NOTHING)
	date = models.DateTimeField()
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)
	discount = models.DecimalField(max_digits=22, decimal_places=2, default=0)


	def total_paid(self):
		total_paid = 0
		# invoice_money_portions = InvoiceMoneyPortion.objects.filter(invoice=self.id)
		invoice_money_portions = Payment.objects.filter(payment_for="INVOICE", payment_for_id=self.id)
		for invoice_money_portion in invoice_money_portions:
			total_paid += float(invoice_money_portion.rated_value)
		return total_paid

	total_paid = property(total_paid)

	def subtotal(self):
		items = InvoiceItem.objects.filter(invoice=self.id)
		subtotal = 0
		for item in items:
			subtotal += item.buying_pack_price * item.total_packs
		return subtotal

	subtotal = property(subtotal)

	def VAT_Value(self):
		VAT_Value = 0
		items = InvoiceItem.objects.filter(invoice=self.id)
		for item in items:
			VAT_Value += item.vat_price
		return VAT_Value

	VAT_Value = property(VAT_Value)


	def total_items(self):
		total_items = 0
		invoice_items = InvoiceItem.objects.filter(invoice=self.id)
		for item in invoice_items:
			total_items += item.total_items
		return total_items

	total_items = property(total_items)


	def total_discount(self):
		total_discount = float(self.discount)
		items = InvoiceItem.objects.filter(invoice=self.id)
		for item in items:
			total_discount += float(item.discount_price)

		return total_discount

	total_discount = property(total_discount)


	def total_cost(self):
		total_cost = (float(self.VAT_Value) + float(self.subtotal)) - float(self.total_discount)
		return total_cost

	total_cost = property(total_cost)


	def balance(self):
		balance = float(self.total_cost) - float(self.total_paid)
		return balance

	balance = property(balance)


	def status(self):
		status = round(float(self.total_cost) - float(self.total_paid), 2)
		if status < float(0):
			status = "CHANGE"
		elif status == 0:
			status = "CLEARED"
		elif status > float(0):
			status = "BALANCE"
		return status

	status = property(status)

	def __str__(self):
		return f'Invoice: {self.invoice_number}'



class InvoiceItem(models.Model):
	invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
	stock = models.ForeignKey(Stock, on_delete=models.CASCADE, blank=True, null=True)
	manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
	vat_price = models.DecimalField(max_digits=22, decimal_places=4)
	vat_percentage = models.DecimalField(max_digits=22, decimal_places=4)
	discount_price = models.DecimalField(max_digits=22, decimal_places=4)
	discount_percentage = models.DecimalField(max_digits=22, decimal_places=4)
	total_packs = models.IntegerField(blank=True, null=True)
	pack_size = models.IntegerField(blank=True, null=True)
	buying_pack_price = models.DecimalField(max_digits=22, decimal_places=4)
	total_buying_pack_price = models.DecimalField(max_digits=22, decimal_places=4)
	markup = models.DecimalField(max_digits=22, decimal_places=4, blank=True, null=True)
	selling_price = models.DecimalField(max_digits=22, decimal_places=4, blank=True, null=True)
	expiration_date = models.DateTimeField(blank=True, null=True)
	batch_number = models.CharField(max_length=40)


	def total_items(self):
		return self.total_packs * self.pack_size

	total_items = property(total_items)

	def stock_value(self):
		stock_value = self.total_packs * self.pack_size * self.stock.selling_price
		return stock_value
	stock_value = property(stock_value)

	def subtotal(self):
		subtotal = float(self.total_packs) * float(self.total_buying_pack_price)
		return subtotal
	subtotal = property(subtotal)

	def total_cost(self):
		total_cost = float(self.subtotal) - float(self.discount_price) + float(self.vat_price)
		return total_cost

	total_cost = property(total_cost)

	
	def __str__(self):
		return f'Added'


class TemporaryInvoiceItem(models.Model):
	invoice = models.ForeignKey(TemporaryInvoice, on_delete=models.CASCADE)
	stock = models.ForeignKey(Stock, on_delete=models.CASCADE, blank=True, null=True)
	manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
	vat_price = models.DecimalField(max_digits=22, decimal_places=4)
	vat_percentage = models.DecimalField(max_digits=22, decimal_places=4)
	discount_price = models.DecimalField(max_digits=22, decimal_places=4)
	discount_percentage = models.DecimalField(max_digits=22, decimal_places=4)
	total_packs = models.IntegerField(blank=True, null=True)
	pack_size = models.IntegerField(blank=True, null=True)
	buying_pack_price = models.DecimalField(max_digits=22, decimal_places=4)
	total_buying_pack_price = models.DecimalField(max_digits=22, decimal_places=4)
	markup = models.DecimalField(max_digits=22, decimal_places=4, blank=True, null=True) #this is markup price not percentage
	selling_price = models.DecimalField(max_digits=22, decimal_places=4, blank=True, null=True)
	expiration_date = models.DateTimeField(blank=True, null=True)
	batch_number = models.CharField(max_length=40)

	discount_number = models.DecimalField(max_digits=22, decimal_places=4, default=0)
	selling_price_number = models.DecimalField(max_digits=22, decimal_places=4, default=0)
	selling_price_type = models.CharField(max_length=40, default="SELLING PRICE")
	discount_type = models.CharField(max_length=40, default="DISCOUNT PRICE")



class ReturnReason(models.Model):
	shortcut = models.CharField(max_length=20)
	details = models.CharField(max_length=40)
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)
	status = models.BooleanField(default=True)



class ReturnOut(models.Model):
	batch = models.ForeignKey(Batch, on_delete=models.DO_NOTHING, null=True, blank=True)
	reason = models.ForeignKey(ReturnReason, on_delete=models.DO_NOTHING)
	notes = models.CharField(max_length=255, default='')
	refund_amount = models.DecimalField(max_digits=15,decimal_places=2)
	total_units = models.IntegerField(blank=True, null=True)
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	date = models.DateTimeField(blank=True, null=True)
	deleted = models.BooleanField(default=False)

	def paid_refund_value(self):
		paid_refund_value = 0
		# portions = RefundReturnOutMoneyPortion.objects.filter(return_out=self.id)
		portions = Payment.objects.filter(payment_for="RETURN_OUT_REFUND", payment_for_id=self.id)
		for portion in portions:
			paid_refund_value = paid_refund_value + portion.rated_value
		return paid_refund_value 

	paid_refund_value = property(paid_refund_value)

	def balance(self):
		balance = float(self.refund_amount) - float(self.paid_refund_value)
		return float(round(balance, 2))

	balance = property(balance)


	def status(self):
		status = float(self.refund_amount) - float(self.paid_refund_value)
		if status > 0:
			status = "BALANCE"
		elif status == 0:
			status = "CLEARED"
		elif status < 0:
			status = "CHANGE"
		return status

	status = property(status)
	
	def __str__(self):
		return f'{ self.batch.stock }'


class CreditNote(models.Model):
	sale_transaction = models.ForeignKey('payments.SaleTransaction', on_delete=models.DO_NOTHING, blank=True, null=True)
	reason = models.ForeignKey(ReturnReason, on_delete=models.DO_NOTHING, null=True, blank=True)
	notes = models.CharField(max_length=255, default='')
	refund_amount = models.DecimalField(max_digits=15,decimal_places=2)
	date = models.DateTimeField()
	
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)


	def total_units(self):
		returns_inn = ReturnInn.objects.filter(credit_note=self.id)
		total_units = 0
		for return_inn in returns_inn:
			total_units += return_inn.total_units
		return total_units

	total_units = property(total_units)


	def ultimate_credit_note_number(self):
		try:
		    configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
		except Exception as e:
			HttpResponseRedirect('client_settings_page')
			
		a = str(self.id).zfill(6)
		b = str(configuration.invoice_number_prefix) + "-CR-"
		return b + a

	ultimate_credit_note_number = property(ultimate_credit_note_number)


	def paid_refund_value(self):
		paid_refund_value = 0
		# portions = RefundReturnInnMoneyPortion.objects.filter(credit_note=self.id)
		portions = Payment.objects.filter(payment_for="CREDIT_NOTE", payment_for_id=self.id)
		for portion in portions:
			paid_refund_value = paid_refund_value + portion.rated_value
		return paid_refund_value 

	paid_refund_value = property(paid_refund_value)


	def balance(self):
		balance = float(self.refund_amount) - float(self.paid_refund_value)
		return balance

	balance = property(balance)


	def status(self):
		status = float(self.refund_amount) - float(self.paid_refund_value)
		if status > 0:
			status = "BALANCE"
		elif status == 0:
			status = "CLEARED"
		elif status < 0:
			status = "CHANGE"
		return status

	status = property(status)



class ReturnInn(models.Model):
	sale = models.ForeignKey('payments.Sale', on_delete=models.DO_NOTHING, null=True, blank=True)
	credit_note = models.ForeignKey("enventory.CreditNote", on_delete=models.CASCADE, blank=True, null=True)
	stock = models.ForeignKey(Stock, on_delete=models.DO_NOTHING, null=True, blank=True)
	sale_value = models.DecimalField(max_digits=15,decimal_places=2)
	total_units = models.IntegerField(blank=True, null=True)
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)


	def value(self):
		return round(self.sale.unit_price * self.total_units, 2)

	value = property(value)


	def __str__(self):
		return f'{ self.sale.stock }'



	
class Lable(models.Model):
	text = models.TextField()
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	deleted = models.BooleanField(default=False)

