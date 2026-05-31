from django.db import models
from django.utils.timezone import now

class FiscalDevice(models.Model):
    """Stores environmental secrets and properties for virtual devices."""
    device_id = models.CharField(max_length=50, unique=True)
    serial_no = models.CharField(max_length=100)
    activation_key = models.CharField(max_length=100)
    company_name = models.CharField(max_length=200, blank=True)
    is_test_mode = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    # Paths for dynamic multi-device certificate loading
    cert_path = models.CharField(max_length=255, default="fiscalisation/certs/certificate.crt")
    private_key_path = models.CharField(max_length=255, default="fiscalisation/certs/decrypted_key.key")
    
    registered_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.company_name} TILL ({self.device_id})"


class FiscalState(models.Model):
    """Maintains active state parameters required to chain hashes locally."""
    device = models.OneToOneField(FiscalDevice, on_delete=models.CASCADE, related_name="state")
    fiscal_day_no = models.IntegerField(default=1)
    receipt_counter = models.IntegerField(default=0)  # Resets to 0 on openDay
    receipt_global_no = models.IntegerField(default=0)  # Continuous increment tracking
    is_day_open = models.BooleanField(default=False)
    current_day_date = models.DateField(null=True, blank=True)
    day_opened_at = models.DateTimeField(null=True, blank=True,
        help_text="Wall-clock timestamp when openDay succeeded. Used to "
                  "compute hours-open and warn before ZIMRA's max-hours cap.")
    last_receipt_hash = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Fiscal States"
    
    def reset_for_new_day(self, next_day_no, day_date):
        """Prepares state variables when openDay succeeds.

        Clears last_receipt_hash because the receipt-signature chain RESETS
        at each fiscal day (spec section 12.2.1: previousReceiptHash is not
        used when receipt is first in fiscal day).
        """
        from .services import zimra_now
        self.fiscal_day_no = next_day_no
        self.receipt_counter = 0
        self.last_receipt_hash = None
        self.is_day_open = True
        self.current_day_date = day_date
        self.day_opened_at = zimra_now()
        self.save()

    def __str__(self):
        return f"Device {self.device.device_id} | Day {self.fiscal_day_no} - {'OPEN' if self.is_day_open else 'CLOSED'}"


class FiscalReceipt(models.Model):
    """Manages the lifecycle of generated invoices from local print to sync."""
    SYNC_CHOICES = [
        ('PENDING', 'Pending Sync'),
        ('SUCCESS', 'Synced to ZIMRA'),
        ('FAILED', 'Rejected by ZIMRA'),
    ]
    RECEIPT_TYPES = [
        ('FISCALINVOICE', 'Fiscal Invoice'),
        ('CREDITNOTE', 'Credit Note'),
        ('DEBITNOTE', 'Debit Note'),
    ]
    
    
    fiscal_state = models.ForeignKey(FiscalState, on_delete=models.CASCADE, related_name="receipts")
    fiscal_day_no = models.IntegerField()
    receipt_global_no = models.IntegerField()
    receipt_counter = models.IntegerField()
    receipt_type = models.CharField(max_length=20, choices=RECEIPT_TYPES, default='FISCALINVOICE')
    
    # Links to your main business tables
    invoice_no = models.CharField(max_length=100, unique=True, help_text="Local SaleTransaction ID reference")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Offline Fingerprints for immediate thermal print rendering
    local_hash = models.CharField(max_length=255)
    local_signature = models.TextField()
    qr_code_string = models.TextField(help_text="Raw verification URL data used for offline QR prints")
    
    # The pre-signed package prepared for background sync workers
    prepared_payload = models.JSONField(help_text="The exact JSON payload built by prepareReceipt")
    
    # Post-Sync records returned from ZIMRA
    sync_status = models.CharField(max_length=15, choices=SYNC_CHOICES, default='PENDING')
    zimra_receipt_id = models.IntegerField(null=True, blank=True)
    zimra_response_log = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Inv {self.invoice_no} | Global #{self.receipt_global_no} [{self.sync_status}]"


class FiscalDaySummary(models.Model):
    """Saves Z-Report parameters to handle day closing securely."""
    fiscal_state = models.ForeignKey(FiscalState, on_delete=models.CASCADE)
    fiscal_day_no = models.IntegerField()
    day_date = models.DateField()
    total_receipts_processed = models.IntegerField(default=0)
    total_sales_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Stores compiled tax breakdowns required for closeDay arrays
    closing_counters_payload = models.JSONField(null=True, blank=True)
    closing_response = models.JSONField(null=True, blank=True)
    is_closed_successfully = models.BooleanField(default=False)
    closed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['fiscal_state', 'fiscal_day_no']
        verbose_name_plural = "Fiscal Day Summaries"

    def __str__(self):
        return f"Day {self.fiscal_day_no} Summary - Closed: {self.is_closed_successfully}"