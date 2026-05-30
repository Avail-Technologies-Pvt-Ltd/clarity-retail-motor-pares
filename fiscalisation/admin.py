from django.contrib import admin

from .models import *

admin.site.register(FiscalDevice)
admin.site.register(FiscalState)
admin.site.register(FiscalReceipt)
admin.site.register(FiscalDaySummary)
