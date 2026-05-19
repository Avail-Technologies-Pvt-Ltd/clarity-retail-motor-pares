from django.contrib import admin

from .models import *


admin.site.register(VATCode)
admin.site.register(PaymentMethod)
admin.site.register(SaleTransaction)
admin.site.register(Sale)
admin.site.register(Payment)
admin.site.register(ExpensesType)
admin.site.register(Expense)

