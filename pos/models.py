from django.db import models

from datetime import datetime, date, timedelta

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from accounts.models import ClientSetting





'''
CLASSES HERE 
    CartItem
    ReceiptPaymentEssential

'''

class CartItem(models.Model):
    stock = models.ForeignKey('enventory.Stock', on_delete=models.CASCADE)
    unit_price = models.DecimalField(max_digits=22,decimal_places=4)
    VAT = models.DecimalField(max_digits=22,decimal_places=4, default=0)
    buying_unit_price = models.DecimalField(max_digits=22,decimal_places=4, default=0)
    quantity = models.PositiveIntegerField(default=0)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    used_baches_data = models.CharField(max_length=30, blank=True, null=True)
    used_baches_quantities_data = models.CharField(max_length=30, blank=True, null=True)


class ReceiptPaymentEssential(models.Model):
    discount = models.DecimalField(max_digits=22,decimal_places=4, default=0)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)


class Quotation(models.Model):
    expiration_date = models.DateTimeField()
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    customer = models.ForeignKey('accounts.CustomerAccount', on_delete=models.CASCADE, blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    just_created = models.BooleanField(default=True)
    is_sold = models.BooleanField(default=False)

    def ultimate_quotation_number(self):
        try:
            configuration = ClientSetting.objects.filter(deleted=False, status=True)[0]
        except Exception as e:
            HttpResponseRedirect('client_settings_page')
            
        a = str(self.id).zfill(6)
        b = str(configuration.invoice_number_prefix)
        return b + a

    ultimate_quotation_number = property(ultimate_quotation_number)


    def is_expired(self):
        if self.expiration_date.date() < datetime.today().date():
            return True
        return False

    is_expired = property(is_expired)


    def total_items(self):
        total_items = QuotationItem.objects.filter(quotation=self.id).count()
        return total_items

    total_items = property(total_items)


    def total_price(self):
        total_price = 0
        quotation_items = QuotationItem.objects.filter(quotation=self.id)
        for item in quotation_items:
            total_price += item.total_price
        return total_price

    total_price = property(total_price)


    def status(self):
        if self.is_sold:
            return "Sold"

        if self.is_expired:
            return "Expired"

        if self.total_items < 1:
            return "Empty"

        if not self.is_active:
            return "Deactivated"

        return "Active"

    status = property(status)

    def color(self):
        if self.is_sold:
            return "blue"

        if self.is_expired:
            return "red"

        if self.total_items < 1:
            return "black"

        if not self.is_active:
            return "gray"

        return "green"

    color = property(color)




class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE)
    stock = models.ForeignKey('enventory.Stock', on_delete=models.CASCADE)
    unit_price = models.DecimalField(max_digits=22,decimal_places=4)
    VAT = models.DecimalField(max_digits=22,decimal_places=4, default=0)
    buying_unit_price = models.DecimalField(max_digits=22,decimal_places=4, default=0)
    quantity = models.PositiveIntegerField(default=0)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.stock.product.title} X {self.quantity}"

    def total_price(self):
        total_price = (self.VAT + self.unit_price) * self.quantity
        return total_price 

    total_price = property(total_price)
    
    