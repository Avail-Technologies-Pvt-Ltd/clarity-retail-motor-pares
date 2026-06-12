import uuid
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models
from datetime import datetime, date, timezone
from django.utils.timezone import localdate




'''
CLASSES HERE:
	User
	Branch
	Supplier
	ClientSetting
	Manufacturer
	CustomerAccount
	PrinterCase
	Note
'''
class User(AbstractUser):
	ROLES = {
		('Sales Rep','Sales Rep'),
		('Supervisor','Supervisor'),
		('Data Analyst','Data Analyst'),

		('Supervisor, Sales Rep','Supervisor, Sales Rep'),
		('Data Analyst, Sales Rep','Data Analyst, Sales Rep'),

		('Data Analyst, Supervisor','Data Analyst, Supervisor'),

		('Data Analyst, Supervisor, Sales Rep','Data Analyst, Supervisor, Sales Rep'),
	}
	phone_number = models.CharField(max_length=30)
	address = models.TextField(max_length=255)
	roles = models.CharField(max_length=1000)
	e_signature_link = models.TextField(max_length=255, default="", blank=True, null=True)
	created_by = models.ForeignKey('User', on_delete=models.DO_NOTHING, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	status = models.BooleanField(default=True)
	deleted = models.BooleanField(default=False)



class Branch(models.Model):
	# Contact Information
	manager = models.CharField(max_length=20, blank=True, null=True)
	phone = models.CharField(max_length=20, blank=True, null=True)
	email = models.EmailField(blank=True, null=True)
	
	# Address
	branch_name = models.CharField(max_length=100)
	address = models.CharField(max_length=255, blank=True)
	city = models.CharField(max_length=100, blank=True)
	country = models.CharField(max_length=50, default='ZW')
	type = models.CharField(max_length=50, default='STORE')
	
	# Status
	is_active = models.BooleanField(default=True)
	is_local = models.BooleanField(default=True)
	
	# Sync
	branch_id = models.CharField(max_length=100, default='', blank=True, null=True) #uuid from central server
	branch_verification_key = models.CharField(max_length=300, default="")
	sync_url = models.CharField(max_length=300, default="")
	last_sync_time = models.CharField(max_length=300, default="")
	last_sync_user = models.CharField(max_length=300, default="")
	
	# Timestamps
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	@property
	def code(self):
		type_prefix = self.type[:3].upper() if self.type else "XX"
		return f"{type_prefix}-{str(self.id).zfill(4)}"
			
	
	def __str__(self):
		return f"{self.branch_name} ({self.id})"



class Supplier(models.Model):
	global_id = models.UUIDField(unique=True, null=True, blank=True)
	version = models.IntegerField(default=1)
	needs_sync = models.BooleanField(default=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_by_branch = models.ForeignKey('Branch', on_delete=models.DO_NOTHING, related_name='created_%(class)s_records', null=True, blank=True)
	updated_by_branch = models.ForeignKey('Branch', on_delete=models.DO_NOTHING, related_name='updated_%(class)s_records', null=True, blank=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	
	company_name = models.CharField(max_length=30)
	registration_number = models.CharField(max_length=100, blank=True, null=True, default='')
	phone_number = models.CharField(max_length=50, blank=True, null=True, default='')
	email = models.CharField(max_length=50, blank=True, null=True, default='')
	address = models.TextField(max_length=255, blank=True, null=True, default='')
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	status = models.BooleanField(default=True)
	deleted = models.BooleanField(default=False)

	def __str__(self):
		return f'{self.company_name}'


class ClientSetting(models.Model):
	configuration_name = models.CharField(max_length=30)
	company_name = models.CharField(max_length=30)
	address = models.TextField(max_length=255, blank=True, null=True)
	tel = models.CharField(max_length=90)
	tin_number = models.CharField(max_length=30)
	prz_number = models.CharField(max_length=30)
	vat_number = models.CharField(max_length=30)
	invoice_number_prefix = models.CharField(max_length=30)

	bank_1_bank_name = models.CharField(max_length=30)
	bank_1_account_name = models.CharField(max_length=30)
	bank_1_name_nostro = models.CharField(max_length=30)
	bank_1_name_zig = models.CharField(max_length=30)

	branch_verification_key = models.CharField(max_length=300, default="")
	branch_id = models.CharField(max_length=300, default=0)
	branch_name = models.CharField(max_length=100, blank=True, null=True)
	sync_url = models.CharField(max_length=300, default="")
	last_sync_time = models.CharField(max_length=300, default="")
	last_sync_user = models.CharField(max_length=300, default="")

	company_registration = models.CharField(max_length=30)
	email = models.TextField(max_length=255, blank=True, null=True)
	# logo = models.ImageField(blank=True, upload_to='images/ClientSettings')
	thank_you_message = models.TextField(max_length=1000, blank=True, null=True)
	status = models.BooleanField(default=True)
	online_update_minute_intervals = models.DecimalField(max_digits=10,decimal_places=0, default=5)
	expiration_warning = models.DecimalField(max_digits=10,decimal_places=0)
	pagination_slice_leangth = models.DecimalField(max_digits=10,decimal_places=0, default=20)
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
	updated_at = models.DateTimeField(auto_now=True)
	deleted = models.BooleanField(default=False)
	subscription_expiration_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
	hosting_email = models.CharField(max_length=100, default="")
	hosting_email_password = models.CharField(max_length=100, default="")
	notification_receiving_email = models.CharField(max_length=100, default="")
	# notification_receiving_phone_number = models.CharField(max_length=100, default="")


	def __str__(self):
		return f'{self.configuration_name}'


class Manufacturer(models.Model):
	global_id = models.UUIDField(unique=True, null=True, blank=True)
	version = models.IntegerField(default=1)
	needs_sync = models.BooleanField(default=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_by_branch = models.ForeignKey('Branch', on_delete=models.DO_NOTHING, related_name='created_%(class)s_records', null=True, blank=True)
	updated_by_branch = models.ForeignKey('Branch', on_delete=models.DO_NOTHING, related_name='updated_%(class)s_records', null=True, blank=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	
	company_name = models.CharField(max_length=30)
	registration_number = models.CharField(max_length=100, default='')
	phone_number = models.CharField(max_length=50, blank=True, null=True, default='')
	email = models.CharField(max_length=50, blank=True, null=True, default='')
	address = models.TextField(max_length=255, blank=True, null=True, default='')
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	status = models.BooleanField(default=True)
	deleted = models.BooleanField(default=False)

	def __str__(self):
		return f'{self.company_name}'


class CustomerAccount(models.Model):
	global_id = models.UUIDField(unique=True, null=True, blank=True)
	version = models.IntegerField(default=1)
	needs_sync = models.BooleanField(default=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_by_branch = models.ForeignKey('Branch', on_delete=models.DO_NOTHING, related_name='created_%(class)s_records', null=True, blank=True)
	updated_by_branch = models.ForeignKey('Branch', on_delete=models.DO_NOTHING, related_name='updated_%(class)s_records', null=True, blank=True)
	deleted_at = models.DateTimeField(null=True, blank=True)
	
	company_name = models.CharField(max_length=30)
	phone_number = models.CharField(max_length=50, blank=True, null=True, default='')
	email = models.CharField(max_length=50, blank=True, null=True, default='')
	address = models.TextField(max_length=255, blank=True, null=True, default='')

	balance = models.IntegerField(default=0)
	credit_limit = models.IntegerField(default=0)

	tin_number = models.CharField(max_length=30,blank=True, null=True)
	prz_number = models.CharField(max_length=30,blank=True, null=True)
	vat_number = models.CharField(max_length=30,blank=True, null=True)

	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	status = models.BooleanField(default=True)
	deleted = models.BooleanField(default=False)

class PrinterCase(models.Model):
	printer_name = models.CharField(max_length=30)
	client_node = models.CharField(max_length=30)
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	status = models.BooleanField(default=True)
	deleted = models.BooleanField(default=False)


class Note(models.Model):
	text = models.CharField(max_length=1000)
	
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	status = models.BooleanField(default=True)
	deleted = models.BooleanField(default=False)

	


	
