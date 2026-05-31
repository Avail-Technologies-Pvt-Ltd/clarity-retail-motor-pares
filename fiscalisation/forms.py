"""Forms for device-management UI."""

from django import forms

from .models import FiscalDevice


class FiscalDeviceForm(forms.ModelForm):
    """Add or edit a device. activation_key is shown only at add time
    because once registered it isn't needed for day-to-day operation."""

    class Meta:
        model = FiscalDevice
        fields = [
            'device_id', 'serial_no', 'activation_key',
            'company_name', 'is_test_mode',
        ]
        widgets = {
            'device_id': forms.TextInput(attrs={'placeholder': 'e.g. 35454', 'class': 'form-control'}),
            'serial_no': forms.TextInput(attrs={'placeholder': 'e.g. testserial2', 'class': 'form-control'}),
            'activation_key': forms.TextInput(attrs={'placeholder': 'e.g. 00082671 (8 digits, zero-padded)', 'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'placeholder': 'Taxpayer name shown on receipts', 'class': 'form-control'}),
            'is_test_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'device_id': "ZIMRA-issued device ID.",
            'activation_key': "8-digit activation key from ZIMRA. Zero-pad shorter values (e.g. '82671' -> '00082671').",
            'is_test_mode': "Tick for ZIMRA test environment, untick for production.",
        }


class CertUploadForm(forms.Form):
    """Upload a pre-existing certificate + private key pair (e.g. for migrating
    a device already registered elsewhere)."""

    certificate = forms.FileField(
        help_text="ZIMRA-issued .crt file in PEM format.",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.crt,.pem'}),
    )
    private_key = forms.FileField(
        help_text="Matching unencrypted private key (.key, PEM).",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.key,.pem'}),
    )
