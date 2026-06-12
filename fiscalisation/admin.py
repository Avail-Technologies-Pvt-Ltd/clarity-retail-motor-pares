from django.contrib import admin

from .models import *

# admin.site.register(FiscalServer)
# admin.site.register(FiscalDevice)
# admin.site.register(FiscalState)
# admin.site.register(FiscalReceipt)
# admin.site.register(FiscalDaySummary)

admin.site.register(FiscalisationSettings)
admin.site.register(FiscalReceiptSequence)
admin.site.register(FiscalReceipt)
admin.site.register(SyncQueue)
admin.site.register(SyncLog)
