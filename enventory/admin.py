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







# admin.site.register(TemporaryInvoiceItem)
# admin.site.register(TemporaryInvoice)
#, ReturnOutAdmin)
# admin.site.register(Sale)
# admin.site.register(ClaimForm)
# admin.site.register(ClaimFormProduct)
# admin.site.register(Lable)
# admin.site.register(Ricipt)
# admin.site.register(PrintersCase)
# admin.site.register(VATCode)
# admin.site.register(Stock)
# admin.site.register(Batch)
# admin.site.register(Cipher)
# admin.site.register(DrugForm)
# admin.site.register(DrugCategory)
# admin.site.register(PaymentMethod)
# admin.site.register(Prescription, PrescriptionAmin)
# admin.site.register(Refill)
# admin.site.register(ExpensesType, ExpensesTypeAdmin)
# admin.site.register(ProductInCart)
# admin.site.register(Expense)
# admin.site.register(Transaction)
# admin.site.register(MoneyPortion, MoneyPortionAdmin)
# admin.site.register(CombinedMoney, CombinedMoneyAdimn)
