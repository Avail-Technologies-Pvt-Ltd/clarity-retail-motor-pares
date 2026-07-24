from django.contrib import admin

from .models import *

admin.site.register(FiscalisationSettings)
admin.site.register(FiscalReceiptSequence)
admin.site.register(FiscalReceipt)
admin.site.register(SyncQueue)
admin.site.register(SyncLog)
