from django.shortcuts import render
from .models import *

from dateutil.relativedelta import relativedelta
from datetime import datetime as datetime_

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse

from django.contrib.auth.hashers import make_password
import hashlib



def create_backup(request):
	from django.http import FileResponse
	return FileResponse(open('db.sqlite3', 'rb'))

#	html
def add_subscription_page(request):
	recent_state = 'ENTER SUBSCRIPTION KEY HERE'
	if request.method == "POST":
		key = request.POST.get('key')

		today = str(datetime_.today().date())[:10]

		order_profile = OrderProfile.objects.all().first()

		monthly_keys_list = order_profile.monthly_keys.rstrip(",").split(",")
		anual_keys_list = order_profile.anual_keys.rstrip(",").split(",")
		

		if key != "":
			vx = make_password
			key = hashlib.sha256(key.encode('utf-8')).digest().hex()
			print(key)

			if key in monthly_keys_list:

				new_payment = SubscriptionPayment()
				new_payment.duration = "1 month"
				try:
					last_subscription = SubscriptionPayment.objects.all().order_by('created_at').last() 
					new_payment.date_from = last_subscription.date_to + relativedelta(days=1)
					new_payment.date_to = last_subscription.date_to + relativedelta(months=1)
				except:
					new_payment.date_from = today + relativedelta(days=1)
					new_payment.date_to = today + relativedelta(months=1)

				new_payment.subscription_key = key
				new_payment.created_by = request.user
				new_payment.save()

				new_list = ''
				for i in monthly_keys_list:
					if i != key:
						new_list = new_list + f'{ i },'
				order_profile.monthly_keys = new_list
				order_profile.save()
				recent_state = "SUBSCRIPTION SUCCESSFUL"


			elif key in anual_keys_list:

				new_payment = SubscriptionPayment()
				new_payment.duration = "1 year"
				try:
					last_subscription = SubscriptionPayment.objects.all().order_by('created_at').last() 
					new_payment.date_from = last_subscription.date_to + relativedelta(days=1)
					new_payment.date_to = last_subscription.date_to + relativedelta(years=1)
				except:
					new_payment.date_from = today + relativedelta(days=1)
					new_payment.date_to = today + relativedelta(years=1)

				new_payment.subscription_key = key
				new_payment.created_by = request.user
				new_payment.save()

				new_list = ''
				for i in anual_keys_list:
					if i != key:
						new_list = new_list + f'{ i },'
				order_profile.anual_keys = new_list
				order_profile.save()
				recent_state = "SUBSCRIPTION SUCCESSFUL"
			else:
				recent_state = "INVALID KEY"
			


	try:
		last_subscription = SubscriptionPayment.objects.all().order_by('created_at').last()
		order_profile = OrderProfile.objects.all().first()

		# time_left = order_profile.time_left
		expiration_date = last_subscription.date_to
		date = last_subscription.created_at
		active_date = last_subscription.date_from
		duration = last_subscription.duration
	except:
		# time_left = "N/A"
		expiration_date = "N/A"
		date = "N/A"
		active_date = "N/A"
		duration = "N/A"


	try:
		order_profile = OrderProfile.objects.all().first()

		whatsapp = order_profile.whatsapp
		call = order_profile.call
		email = order_profile.email
		website = order_profile.website
	except:
		whatsapp = "N/A"
		call = "N/A"
		email = "N/A"
		website = "N/A"



	contact = {
		'whatsapp': whatsapp,
		'call': call,
		'email': email,
		'website': website,
	}

	subscription_status = {
		'expiration_date': str(expiration_date)[:10],
		'date': str(date)[:10],
		'active_date': str(active_date)[:10],
		'duration': duration,
	}

	old_payments = SubscriptionPayment.objects.all().order_by('created_at').reverse()
	payment_instructions = order_profile.payment_instructions

	context = {
		'subscription_status': subscription_status,
		'contact': contact,
		'recent_state': recent_state,
		'old_payments': old_payments,
		'payment_instructions': payment_instructions,
	}
	return render(request, 'order/subscriptions/add_subscription_page.html', context)






# HELPER FUNCTIONS


# API
def days_from_now(request):
	days = request.GET.get('days')
	today = datetime_.today().date()
	new_date = today + relativedelta(days=int(days))
	return JsonResponse({'new_date': new_date})

# DIRECT PYTHON CALL
def days_from_now_python(days):
	today = datetime_.today().date()
	new_date = today + relativedelta(days=int(days))
	return new_date
