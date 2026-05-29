# fiscalisation/models.py
from django.db import models

class FiscalDevice(models.Model):
    """Store fiscal device information"""
    device_id = models.CharField(max_length=50, unique=True)
    serial_no = models.CharField(max_length=100)
    activation_key = models.CharField(max_length=100)
    company_name = models.CharField(max_length=200, blank=True)
    is_test_mode = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.device_id} - {self.serial_no}"

class FiscalState(models.Model):
    """Track fiscal day and receipt counters"""
    device = models.OneToOneField(FiscalDevice, on_delete=models.CASCADE)
    fiscal_day_no = models.IntegerField(default=1)
    receipt_counter = models.IntegerField(default=1)
    receipt_global_no = models.IntegerField(default=1)
    is_day_open = models.BooleanField(default=False)
    current_day_date = models.DateField(null=True, blank=True)
    last_receipt_hash = models.CharField(max_length=255, blank=True, null=True)
    last_closed_day_no = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Fiscal States"
    
    def __str__(self):
        return f"Day {self.fiscal_day_no} - {'Open' if self.is_day_open else 'Closed'}"

class FiscalReceipt(models.Model):
    """Store receipt history for reference"""
    RECEIPT_TYPES = [
        ('FISCALINVOICE', 'Fiscal Invoice'),
        ('CREDITNOTE', 'Credit Note'),
        ('DEBITNOTE', 'Debit Note'),
    ]
    
    fiscal_state = models.ForeignKey(FiscalState, on_delete=models.CASCADE)
    receipt_global_no = models.IntegerField()
    receipt_counter = models.IntegerField()
    receipt_type = models.CharField(max_length=20, choices=RECEIPT_TYPES)
    invoice_no = models.CharField(max_length=100)
    receipt_id = models.IntegerField(null=True, blank=True)
    server_signature = models.JSONField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    qr_code_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Receipt {self.receipt_global_no} - {self.invoice_no}"

class FiscalDaySummary(models.Model):
    """Store daily closing summaries"""
    fiscal_state = models.ForeignKey(FiscalState, on_delete=models.CASCADE)
    fiscal_day_no = models.IntegerField()
    day_date = models.DateField()
    total_receipts = models.IntegerField(default=0)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closing_response = models.JSONField(null=True, blank=True)
    closed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['fiscal_state', 'fiscal_day_no']
    
    def __str__(self):
        return f"Day {self.fiscal_day_no} - {self.day_date}"