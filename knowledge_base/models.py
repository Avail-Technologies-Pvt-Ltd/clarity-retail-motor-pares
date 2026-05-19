from django.db import models
from enventory.models import Stock





class CarMake(models.Model):
    make = models.CharField(max_length=50)
    logo = models.ImageField(upload_to='images/makes/', blank=True, null=True)

    def __str__(self):
        return self.make


class CarTransmission(models.Model):
    shortcut = models.CharField(max_length=20)
    title = models.CharField(max_length=100)


    def __str__(self):
        return self.title



class CarModel(models.Model):
    engine_number = models.CharField(max_length=50)
    make = models.ForeignKey(CarMake, on_delete=models.CASCADE)  # Toyota
    model = models.CharField(max_length=50)  # Corolla
    year = models.CharField(max_length=20)  # 2015-2020
    car_transmission = models.ForeignKey(CarTransmission, on_delete=models.DO_NOTHING)
    
    class Meta:
        unique_together = ['engine_number', 'make', 'model', 'year', 'car_transmission']
    
    def __str__(self):
        return f"{self.engine_number} {self.make} {self.model} {self.car_transmission} ({self.year})"



class CompatibilityType(models.Model):
    compatibility_type = models.CharField(max_length=50)
    is_compatible = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.compatibility_type}"


class Compatibility(models.Model):
    car_part = models.ForeignKey(Stock, on_delete=models.CASCADE)
    car_model = models.ForeignKey(CarModel, on_delete=models.CASCADE)
    compatibility_type = models.ForeignKey(CompatibilityType, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        unique_together = ['car_part', 'car_model']#, 'compatibility_type']
        verbose_name_plural = 'Compatibilities'
    
    def __str__(self):
        return f"{self.car_part} → {self.car_model}"