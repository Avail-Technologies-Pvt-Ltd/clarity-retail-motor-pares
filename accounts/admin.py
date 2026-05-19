from django.contrib import admin
from .models import User, Supplier, ClientSetting, Manufacturer, Note, PrinterCase, CustomerAccount

# Registering  models.
class UserAdmin(admin.ModelAdmin):
	list_display = ['password','username','first_name','last_name','phone_number','roles']


class SupplierAdmin(admin.ModelAdmin):
	list_display = ['company_name','phone_number','email','address','created_by']


class ClientSettingAdmin(admin.ModelAdmin):
	list_display = ['configuration_name','company_name','address','tel','email','thank_you_message','status']


class ManufacturerAdmin(admin.ModelAdmin):
	list_display = ['company_name','phone_number','email','address','created_by']


class NoteAdmin(admin.ModelAdmin):
	list_display = ['text','created_at','created_by']


class PrinterCaseAdmin(admin.ModelAdmin):
	list_display = ['client_node','printer_name','status']


class CustomerAccountAdmin(admin.ModelAdmin):
	list_display = ['company_name','balance','credit_limit']


admin.site.register(User, UserAdmin)
admin.site.register(Supplier, SupplierAdmin)
admin.site.register(ClientSetting, ClientSettingAdmin)
admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(Note, NoteAdmin)
admin.site.register(PrinterCase, PrinterCaseAdmin)
admin.site.register(CustomerAccount, CustomerAccountAdmin)