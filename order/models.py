from django.db import models

from accounts.models import User

class SubscriptionPayment(models.Model):
	duration = models.CharField(max_length=50)
	date_from = models.DateTimeField()
	date_to = models.DateTimeField()
	subscription_key = models.CharField(max_length=20)
	
	created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
	created_at = models.DateTimeField(auto_now_add=True)


class OrderProfile(models.Model):
	monthly_keys = models.TextField(max_length=50000, blank=True, null=True)
	anual_keys = models.TextField(max_length=50000, blank=True, null=True)
	expiration_date = models.DateTimeField()

	whatsapp = models.CharField(max_length=30, blank=True, null=True)
	call = models.CharField(max_length=30, blank=True, null=True)
	email = models.CharField(max_length=30, blank=True, null=True)
	website = models.CharField(max_length=30, blank=True, null=True)

	payment_instructions = models.TextField(max_length=20000, blank=True, null=True)

	updated_at = models.DateTimeField(auto_now=True)

