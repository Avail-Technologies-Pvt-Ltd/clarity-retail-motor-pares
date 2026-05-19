from django.contrib import admin
from .models import CarMake, CarTransmission, CarModel, Compatibility, CompatibilityType



admin.site.register(CarMake)
admin.site.register(CarTransmission)
admin.site.register(CarModel)
admin.site.register(Compatibility)
admin.site.register(CompatibilityType)