from django.db import models

from accounts.models import User

class SubscriptionPayment(models.Model):
	duration = models.CharField(max_length=50)
	date_from = models.DateTimeField()
	date_to = models.DateTimeField()
	subscription_key = models.CharField(max_length=20)
	
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)


class SubscriptionManager(models.Model):
	monthly_keys = models.TextField(max_length=50000, blank=True, null=True)
	anual_keys = models.TextField(max_length=50000, blank=True, null=True)
	expiration_date = models.DateTimeField()

	whatsapp = models.CharField(max_length=30, blank=True, null=True)
	call = models.CharField(max_length=30, blank=True, null=True)
	email = models.CharField(max_length=30, blank=True, null=True)
	website = models.CharField(max_length=30, blank=True, null=True)

	instructions = models.TextField(max_length=20000, blank=True, null=True)

	updated_at = models.DateTimeField(auto_now=True)


class SyncManager(models.Model):
	sync_url = models.CharField(max_length=100)
	sync_intervals_minutes = models.IntegerField(default=60)
	last_sync_date = models.DateTimeField()
	last_sync_user = models.CharField(max_length=50, default="")
	
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)



class NotificationsManager(models.Model):
	hosting_email = models.CharField(max_length=30)
	hosting_email_password = models.CharField(max_length=255)
	notification_receiving_emails = models.JSONField(default=list, blank=True)
	stock_expiration_warning_days = models.IntegerField(default=60)


class SystemInfo(models.Model):
	company = models.CharField(max_length=30, default="Avail Technologies Pvt Ltd")
	website = models.CharField(max_length=30, default="www.avail.co.zw")

	technologies = models.JSONField(default=list, blank=True)

	support_call = models.CharField(max_length=255, default='+263 78 485 1863')
	support_whatsapp = models.CharField(max_length=255, default="+263 78 610 6154")
	support_email = models.CharField(max_length=255, default="info@avail.co.zw")

	virsion = models.CharField(max_length=20, default=2.0)
	last_update = models.DateTimeField()
