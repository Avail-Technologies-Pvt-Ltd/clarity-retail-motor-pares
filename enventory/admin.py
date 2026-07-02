from django.contrib import admin
from .models import *

class ProductAdmin(admin.ModelAdmin):
	list_display = ['bar_code','title','details']




admin.site.register(Product, ProductAdmin)
admin.site.register(Stock)
admin.site.register(Notification)
admin.site.register(Batch)
admin.site.register(BatchAdjustment)
admin.site.register(BatchAdjustmentReason)
admin.site.register(TemporaryInvoice)
admin.site.register(TemporaryInvoiceItem)
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(ReturnOut)
admin.site.register(ReturnInn)
admin.site.register(Lable)
admin.site.register(ReturnReason)
admin.site.register(CreditNote)
admin.site.register(Department)
admin.site.register(Category)