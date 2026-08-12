from django.contrib import admin
from .models import *

admin.site.register(SubscriptionManager)
admin.site.register(SubscriptionPayment)
admin.site.register(SyncManager)
admin.site.register(NotificationsManager)