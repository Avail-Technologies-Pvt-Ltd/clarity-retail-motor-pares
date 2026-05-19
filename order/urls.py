from django.urls import path
from .import views


urlpatterns = [
	# html
	path('create_backup', views.create_backup, name='create_backup'),
	path('add_subscription_page', views.add_subscription_page, name='add_subscription_page'),

	
	# path('subscription_topup', views.subscription_topup, name='subscription_topup'),


	# HELPER FUNCTIONS
	path('days_from_now', views.days_from_now, name='days_from_now'),
]