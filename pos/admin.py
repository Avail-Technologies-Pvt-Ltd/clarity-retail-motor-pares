from django.contrib import admin

from .models import *


admin.site.register(QuotationItem)
admin.site.register(Quotation)
admin.site.register(CartItem)