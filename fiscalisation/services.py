# fiscalisation/services.py - Updated with ALWAYS print payload

import json
import requests
import logging
from datetime import date
from decimal import Decimal
from typing import Dict, Optional, List
from django.utils import timezone
from django.db import transaction

from .models import (
    FiscalisationSettings, 
    FiscalReceipt, 
    FiscalReceiptSequence, 
    SyncQueue,
    SyncLog
)

logger = logging.getLogger(__name__)


class BinaryAPIClient:
    """Client for Binary Software API"""
    
    def __init__(self):
        self.settings = FiscalisationSettings.get_settings()
        self.base_url = self.settings.api_base_url.rstrip('/')
        self.device_id = self.settings.device_id
        self.machine_code = self.settings.machine_code
        self.api_password = self.settings.api_password
    
    def _make_request(self, method, endpoint, params=None, data=None):
        if endpoint.startswith('/'):
            url = f"{self.base_url}{endpoint}"
        else:
            url = f"{self.base_url}/{endpoint}"
        
        print(f"\n{'='*80}")
        print(f"API REQUEST: {method} {url}")
        print(f"{'='*80}")
        
        if data:
            print(f"\n📤 PAYLOAD BEING SENT:")
            print(json.dumps(data, indent=2))
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=30)
            else:
                response = requests.post(url, params=params, json=data, timeout=30)
            
            print(f"\n📥 RESPONSE:")
            print(f"  Status Code: {response.status_code}")
            
            response_text = response.text.strip()
            
            if response.status_code == 200:
                print(f"  ✅ SUCCESS")
                print(f"  Response: {response_text}")
                return response_text
            else:
                print(f"  ❌ ERROR - Status {response.status_code}")
                print(f"  Response: {response_text[:500]}")
                try:
                    return response.json()
                except:
                    return {'error': response_text, 'status_code': response.status_code}
                    
        except Exception as e:
            print(f"  ❌ REQUEST ERROR: {e}")
            return {'error': str(e)}
    
    def get_status(self) -> Dict:
        return self._make_request('GET', '/GetZimraStatus', params={"DeviceID": self.device_id})
    
    def get_config_tax(self) -> Dict:
        return self._make_request('GET', '/GetConfigTax', params={"DeviceID": self.device_id})
    
    def submit_invoice(self, invoice_data: Dict) -> str:
        """Submit invoice to Binary API - returns QR code URL string"""
        return self._make_request('POST', '/ThePost', data=invoice_data)



class FiscalisationService:
    """Main service for fiscalisation operations"""
    
    def __init__(self):
        self.settings = FiscalisationSettings.get_settings()
        self.api_client = BinaryAPIClient()
    
    def is_fiscalisation_active(self) -> bool:
        return self.settings.is_fiscalisation_active()
    
    def pause_fiscalisation(self, reason="", user=""):
        self.settings.pause(reason, user)
    
    def resume_fiscalisation(self):
        self.settings.resume()
    
    @transaction.atomic
    def create_fiscal_receipt(self, 
                          internal_invoice_id: int,
                          internal_invoice_number: str,
                          total_amount: Decimal,
                          payment_method: str,
                          line_items: List[Dict],
                          payments: List[Dict] = None,
                          payment_amount: Decimal = None,
                          transaction_date: date = None,
                          transaction_time: str = None,
                          currency: str = "USD",
                          buyer_info: Dict = None,
                          receipt_type: str = "FISCALINVOICE",
                          original_invoice_number: str = None,
                          internal_sale_id: int = None) -> FiscalReceipt:
        
        next_numbers = FiscalReceiptSequence.get_next_number()
        
        if not transaction_date:
            transaction_date = timezone.now().date()
        if not transaction_time:
            transaction_time = timezone.now().strftime('%H:%M:%S')
        
        # Handle payments
        if payments and len(payments) > 0:
            first_payment = payments[0]
            payment_method = first_payment.get('method', payment_method)
            payment_amount = Decimal(str(first_payment.get('amount', total_amount)))
        elif payment_amount is None:
            payment_amount = total_amount
        
        tax_breakdown = self._calculate_tax_breakdown(line_items)
        
        receipt = FiscalReceipt(
            internal_sale_id=internal_sale_id,
            internal_invoice_id=internal_invoice_id,
            internal_invoice_number=internal_invoice_number,
            fiscal_receipt_number=next_numbers['daily'],
            fiscal_receipt_global_no=next_numbers['global'],
            receipt_type=receipt_type,
            currency=currency,
            transaction_date=transaction_date,
            transaction_time=transaction_time,
            total_amount=total_amount,
            subtotal=tax_breakdown.get('subtotal', 0),
            tax_amount=tax_breakdown.get('total_tax', 0),
            tax_breakdown=tax_breakdown,
            payment_method=payment_method,
            payment_amount=payment_amount,
            payments=payments or [],
            line_items=line_items,
            original_invoice_number=original_invoice_number or "",
        )
        
        if buyer_info:
            receipt.buyer_name = buyer_info.get('name', '')
            receipt.buyer_tin = buyer_info.get('tin', '')
            receipt.buyer_vat = buyer_info.get('vat', '')
            receipt.buyer_address = buyer_info.get('address', '')
            receipt.buyer_phone = buyer_info.get('phone', '')
            receipt.buyer_email = buyer_info.get('email', '')
        
        if not self.is_fiscalisation_active():
            receipt.status = FiscalReceipt.STATUS_BYPASSED
        
        receipt.save()
        
        if self.is_fiscalisation_active() and receipt_type == "FISCALINVOICE":
            self.add_to_sync_queue(receipt)
        
        return receipt
    
    def add_to_sync_queue(self, receipt: FiscalReceipt, priority: int = 0):
        SyncQueue.objects.create(fiscal_receipt=receipt, priority=priority, scheduled_for=timezone.now())
    
    def _calculate_tax_breakdown(self, line_items: List[Dict]) -> Dict:
        tax_groups = {}
        subtotal = Decimal('0')
        
        for item in line_items:
            item_total = Decimal(str(item.get('total', 0)))
            tax_percent = Decimal(str(item.get('tax_percentage', 0)))
            
            # Update old 15% to 15.5%
            if tax_percent == 15:
                tax_percent = Decimal('15.5')
            
            subtotal += item_total
            
            tax_key = float(tax_percent)
            if tax_key not in tax_groups:
                tax_groups[tax_key] = {'sales_total': Decimal('0'), 'tax_amount': Decimal('0')}
            
            tax_groups[tax_key]['sales_total'] += item_total
            if tax_percent > 0:
                tax_amount = item_total * (tax_percent / (100 + tax_percent))
                tax_groups[tax_key]['tax_amount'] += tax_amount
        
        return {
            'subtotal': float(subtotal),
            'total_tax': float(sum(g['tax_amount'] for g in tax_groups.values())),
            'tax_groups': {str(k): {'sales_total': float(v['sales_total']), 'tax_amount': float(v['tax_amount'])} 
                          for k, v in tax_groups.items()}
        }
    
    # def prepare_binary_payload_old(self, receipt: FiscalReceipt) -> Dict:
    #     """Prepare payload matching Binary Software API exactly"""
        
    #     print(f"\n{'='*80}")
    #     print(f"📝 PREPARING PAYLOAD FOR RECEIPT #{receipt.id}")
    #     print(f"{'='*80}")
    #     print(f"  Internal Invoice #: {receipt.internal_invoice_number}")
    #     print(f"  Total Amount: {receipt.total_amount}")
    #     print(f"  Payment Method: {receipt.payment_method}")
    #     print(f"  Payment Amount: {receipt.payment_amount}")
        
    #     # Calculate tax totals
    #     tax_15_sales_total = Decimal('0')
    #     tax_15_amount = Decimal('0')
    #     zero_perc_sales_total = Decimal('0')
    #     zero_perc_tax_amt = Decimal('0')
        
    #     for tax_percent_str, group in receipt.tax_breakdown.get('tax_groups', {}).items():
    #         tax_percent = float(tax_percent_str)
    #         sales_total = Decimal(str(group.get('sales_total', 0)))
    #         tax_amount = Decimal(str(group.get('tax_amount', 0)))
            
    #         if abs(tax_percent - 15.5) < 0.01:
    #             tax_15_sales_total += sales_total
    #             tax_15_amount += tax_amount
    #         elif tax_percent == 0:
    #             zero_perc_sales_total += sales_total
    #             zero_perc_tax_amt += tax_amount
        
    #     # ReceiptDetail - ARRAY of objects
    #     receipt_details = []
    #     for idx, item in enumerate(receipt.line_items):
    #         detail = {
    #             "LineDescription": item.get('description', ''),
    #             "UnitPrice": f"{Decimal(str(item.get('unit_price', 0))):.2f}",
    #             "Quantity": f"{Decimal(str(item.get('quantity', 0))):.2f}",
    #             "Total": f"{Decimal(str(item.get('total', 0))):.2f}",
    #             "IntTaxCode": item.get('int_tax_code', 3),
    #             "StrTaxCode": item.get('str_tax_code', 'C'),
    #             "TaxPercentage": f"{Decimal(str(item.get('tax_percentage', 0))):.2f}",
    #             "receiptLineHSCode": item.get('hs_code', '95069100')
    #         }
    #         receipt_details.append(detail)
        
    #     # TheHeader - ARRAY with correct field names
    #     header = [{
    #         "DocType": receipt.receipt_type,
    #         "DeviceId": self.settings.device_id,
    #         "InvNumber": str(receipt.internal_invoice_id),
    #         "DocCurrency": receipt.currency,
    #         "myYYY_MM_DDdate": receipt.transaction_date.strftime('%Y-%m-%d'),
    #         "My24hrTimeformatwithSeconds": receipt.transaction_time,
    #         "DocumentTotal": f"{receipt.total_amount:.2f}",
    #         "nontaxible_salesAmtTotal": "0.00",
    #         "ZeroPer_Taxamt": f"{zero_perc_tax_amt:.2f}",
    #         "ZeroPerc_SalesAmtTotal": f"{zero_perc_sales_total:.2f}",
    #         "TaxAmt15Perc": f"{tax_15_amount:.2f}",
    #         "Tax15Perc_SalesTotal": f"{tax_15_sales_total:.2f}",
    #         "InvoicenumbertoCredit_debit": "0",
    #         "machinecode": self.settings.machine_code,
    #         "ThePassword": self.settings.api_password,
    #     }]
        
    #     # Add buyer info if present
    #     if receipt.buyer_name:
    #         header[0]["buyerRegisterName"] = receipt.buyer_name[:200]
    #         header[0]["buyerTIN"] = receipt.buyer_tin[:50] if receipt.buyer_tin else ""
    #         if receipt.buyer_vat:
    #             header[0]["VATNumber"] = receipt.buyer_vat[:50]
    #         if receipt.buyer_address:
    #             header[0]["province"] = "Harare"
    #             header[0]["city"] = "Harare"
    #             header[0]["street"] = receipt.buyer_address[:100]
    #             header[0]["houseno"] = "1"
    #         if receipt.buyer_phone:
    #             header[0]["phoneNo"] = receipt.buyer_phone[:20]
    #         if receipt.buyer_email:
    #             header[0]["email"] = receipt.buyer_email[:100]
        
    #     # For credit notes
    #     if receipt.receipt_type == FiscalReceipt.TYPE_CREDIT_NOTE and receipt.original_invoice_number:
    #         header[0]["InvoicenumbertoCredit_debit"] = receipt.original_invoice_number
        
    #     # paymentline - ARRAY of objects
    #     if receipt.payments and len(receipt.payments) > 0:
    #         payment_line = []
    #         for p in receipt.payments:
    #             payment_line.append({
    #                 "PaymentMethodName": p.get('method', 'CASH').upper(),
    #                 "PaymentAmt": f"{Decimal(str(p.get('amount', 0))):.2f}"
    #             })
    #     else:
    #         payment_line = [{
    #             "PaymentMethodName": receipt.payment_method.upper(),
    #             "PaymentAmt": f"{receipt.payment_amount:.2f}"
    #         }]
        
    #     # Complete payload
    #     payload = {
    #         "id": 0,
    #         "ThePassword": None,
    #         "Role": None,
    #         "paymentline": payment_line,
    #         "ReceiptDetail": receipt_details,
    #         "TheHeader": header
    #     }
        
    #     return payload

    # fiscalisation/services.py - Update prepare_binary_payload

    def prepare_binary_payload(self, receipt: FiscalReceipt) -> Dict:
        """Prepare payload matching Binary Software API exactly"""
        
        # Calculate tax totals
        tax_15_sales_total = Decimal('0')
        tax_15_amount = Decimal('0')
        zero_perc_sales_total = Decimal('0')
        zero_perc_tax_amt = Decimal('0')
        
        for tax_percent_str, group in receipt.tax_breakdown.get('tax_groups', {}).items():
            tax_percent = float(tax_percent_str)
            sales_total = Decimal(str(group.get('sales_total', 0)))
            tax_amount = Decimal(str(group.get('tax_amount', 0)))
            
            if abs(tax_percent - 15.5) < 0.01:
                tax_15_sales_total += sales_total
                tax_15_amount += tax_amount
            elif tax_percent == 0:
                zero_perc_sales_total += sales_total
                zero_perc_tax_amt += tax_amount
        
        # ReceiptDetail - ARRAY of objects
        receipt_details = []
        for item in receipt.line_items:
            receipt_details.append({
                "LineDescription": item.get('description', ''),
                "UnitPrice": f"{Decimal(str(item.get('unit_price', 0))):.2f}",
                "Quantity": f"{Decimal(str(item.get('quantity', 0))):.2f}",
                "Total": f"{Decimal(str(item.get('total', 0))):.2f}",
                "IntTaxCode": item.get('int_tax_code', 2),
                "StrTaxCode": item.get('str_tax_code', 'B'),
                "TaxPercentage": f"{Decimal(str(item.get('tax_percentage', 0))):.2f}",
                "receiptLineHSCode": item.get('hs_code', '95069100')
            })
        
        # ============================================================
        # TheHeader - with InvoicenumbertoCredit_debit for credit notes
        # ============================================================
        header = [{
            "DocType": receipt.receipt_type,
            "DeviceId": self.settings.device_id,
            "InvNumber": str(receipt.internal_invoice_id),
            "DocCurrency": receipt.currency,
            "myYYY_MM_DDdate": receipt.transaction_date.strftime('%Y-%m-%d'),
            "My24hrTimeformatwithSeconds": receipt.transaction_time,
            "DocumentTotal": f"{receipt.total_amount:.2f}",
            "nontaxible_salesAmtTotal": "0.00",
            "ZeroPer_Taxamt": f"{zero_perc_tax_amt:.2f}",
            "ZeroPerc_SalesAmtTotal": f"{zero_perc_sales_total:.2f}",
            "TaxAmt15Perc": f"{tax_15_amount:.2f}",
            "Tax15Perc_SalesTotal": f"{tax_15_sales_total:.2f}",
            "machinecode": self.settings.machine_code,
            "ThePassword": self.settings.api_password,
        }]
        
        # ============================================================
        # CRITICAL: Set InvoicenumbertoCredit_debit for credit notes
        # ============================================================
        if receipt.receipt_type == "CREDITNOTE":
            if receipt.original_invoice_number and receipt.original_invoice_number != "0":
                header[0]["InvoicenumbertoCredit_debit"] = receipt.original_invoice_number
                print(f"Credit Note - Original Invoice: {receipt.original_invoice_number}")
            else:
                # This should not happen - credit note must reference an original invoice
                header[0]["InvoicenumbertoCredit_debit"] = "0"
                print("WARNING: Credit note missing original_invoice_number!")
        else:
            # For regular invoices, set to "0"
            header[0]["InvoicenumbertoCredit_debit"] = "0"
        
        # Add buyer info if present
        if receipt.buyer_name:
            header[0]["buyerRegisterName"] = receipt.buyer_name[:200]
            header[0]["buyerTIN"] = receipt.buyer_tin[:50] if receipt.buyer_tin else None
            header[0]["VATNumber"] = receipt.buyer_vat[:50] if receipt.buyer_vat else None
            header[0]["phoneNo"] = receipt.buyer_phone[:20] if receipt.buyer_phone else None
            header[0]["email"] = receipt.buyer_email[:100] if receipt.buyer_email else None
            
            if receipt.buyer_address:
                header[0]["province"] = "Harare"
                header[0]["city"] = "Harare"
                header[0]["street"] = receipt.buyer_address[:100]
                header[0]["houseNo"] = "1"
        
        # paymentline - ARRAY of objects
        if receipt.payments and len(receipt.payments) > 0:
            payment_line = []
            for p in receipt.payments:
                payment_line.append({
                    "PaymentMethodName": p.get('method', 'CASH').upper(),
                    "PaymentAmt": f"{Decimal(str(p.get('amount', 0))):.2f}"
                })
        else:
            payment_line = [{
                "PaymentMethodName": receipt.payment_method.upper(),
                "PaymentAmt": f"{receipt.payment_amount:.2f}"
            }]
        
        # Complete payload
        payload = {
            "id": 0,
            "ThePassword": None,
            "Role": None,
            "paymentline": payment_line,
            "ReceiptDetail": receipt_details,
            "TheHeader": header
        }
        
        return payload



    def sync_receipt(self, receipt: FiscalReceipt) -> bool:
        if not self.is_fiscalisation_active():
            print(f"\n⚠️ SKIPPING: Fiscalisation is paused for receipt #{receipt.id}")
            return False
        
        print(f"\n{'#'*80}")
        print(f"🔄 SYNCING RECEIPT #{receipt.id}")
        print(f"📄 Internal Invoice: {receipt.internal_invoice_number}")
        print(f"💰 Total Amount: {receipt.total_amount}")
        print(f"{'#'*80}")
        
        # Prepare and print the payload
        payload = self.prepare_binary_payload(receipt)
        
        print(f"\n{'='*80}")
        print("📤 COMPLETE PAYLOAD BEING SUBMITTED TO BINARY API")
        print(f"{'='*80}")
        print(json.dumps(payload, indent=2))
        print(f"{'='*80}\n")
        
        # Submit to API
        response = self.api_client.submit_invoice(payload)
        
        # ============================================================
        # CORRECT: Binary API returns a plain string URL on SUCCESS
        # Example: "https://fdmstest.zimra.co.zw/0000035708100620260000000006D899FB0D9E4689BB"
        # ANY string starting with 'http' is a SUCCESS
        # ============================================================
        
        # Check if response is a string (plain text)
        if isinstance(response, str):
            # If it starts with 'http', it's a QR code URL = SUCCESS
            if response.startswith('http'):
                receipt.mark_synced(response, {'qr_url': response})
                print(f"\n✅✅✅ SUCCESS! Receipt #{receipt.id} synced to ZIMRA ✅✅✅")
                print(f"🔗 QR Code URL: {response}")
                return True
            else:
                # Plain text but not a URL = ERROR
                receipt.mark_failed(response)
                print(f"\n❌ FAILED! Receipt #{receipt.id} could not be synced")
                print(f"📛 Error: {response}")
                return False
        
        # If response is a dict (error case from API)
        elif isinstance(response, dict):
            error_msg = response.get('error') or response.get('title') or str(response)
            receipt.mark_failed(error_msg)
            print(f"\n❌ FAILED! Receipt #{receipt.id} could not be synced")
            print(f"📛 Error: {error_msg}")
            if response.get('errors'):
                print(f"Details: {json.dumps(response.get('errors'), indent=2)}")
            return False
        
        # Unexpected response type
        else:
            receipt.mark_failed(f"Unexpected response: {response}")
            print(f"\n❌ FAILED! Unexpected response type: {type(response)}")
            print(f"Response: {response}")
            return False

    def sync_pending_receipts(self, limit: int = 100) -> Dict:
        """Sync all pending receipts"""
        
        print(f"\n{'#'*80}")
        print(f"📡 SYNCING PENDING RECEIPTS (Max: {limit})")
        print(f"{'#'*80}")
        
        results = {'success': 0, 'failed': 0, 'total': 0}
        
        pending = list(FiscalReceipt.objects.filter(
            status=FiscalReceipt.STATUS_PENDING,
            retry_count__lt=self.settings.max_retry_count
        ).order_by('created_at')[:limit])  # ← REMOVED one extra bracket here
        
        print(f"📊 Found {len(pending)} pending receipt(s) to sync\n")
        
        sync_log = SyncLog.objects.create(success=False)
        start_time = timezone.now()
        
        for idx, receipt in enumerate(pending):
            print(f"\n{'─'*40}")
            print(f"Processing {idx+1} of {len(pending)}")
            print(f"{'─'*40}")
            
            results['total'] += 1
            if self.sync_receipt(receipt):
                results['success'] += 1
            else:
                results['failed'] += 1
        
        sync_log.success = results['failed'] == 0
        sync_log.synced_count = results['success']
        sync_log.failed_count = results['failed']
        sync_log.duration_ms = int((timezone.now() - start_time).total_seconds() * 1000)
        sync_log.save()
        
        print(f"\n{'='*80}")
        print(f"📊 SYNC COMPLETE")
        print(f"{'='*80}")
        print(f"  ✅ Success: {results['success']}")
        print(f"  ❌ Failed: {results['failed']}")
        print(f"  📝 Total: {results['total']}")
        print(f"  ⏱️ Duration: {sync_log.duration_ms}ms")
        print(f"{'='*80}\n")
        
        return results

    
    def get_pending_count(self) -> int:
        return FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_PENDING).count()
    
    def get_failed_count(self) -> int:
        return FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_FAILED).count()
    
    def get_bypassed_count(self) -> int:
        return FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_BYPASSED).count()
    
    def get_synced_count(self) -> int:
        return FiscalReceipt.objects.filter(status=FiscalReceipt.STATUS_SYNCED).count()
    
    def retry_failed_receipt(self, receipt_id: int) -> bool:
        print(f"\n🔄 Retrying failed receipt #{receipt_id}")
        try:
            receipt = FiscalReceipt.objects.get(id=receipt_id)
            if receipt.status == FiscalReceipt.STATUS_FAILED:
                receipt.status = FiscalReceipt.STATUS_PENDING
                receipt.retry_count = 0
                receipt.last_error = ""
                receipt.save()
                self.add_to_sync_queue(receipt, priority=10)
                print(f"  ✅ Receipt #{receipt_id} reset to PENDING and queued for retry")
                return True
            else:
                print(f"  ⚠️ Receipt #{receipt_id} status is {receipt.status}, cannot retry")
                return False
        except FiscalReceipt.DoesNotExist:
            print(f"  ❌ Receipt #{receipt_id} not found")
            return False
    
    def void_receipt(self, receipt_id: int) -> bool:
        print(f"\n🗑️ Voiding receipt #{receipt_id}")
        try:
            receipt = FiscalReceipt.objects.get(id=receipt_id)
            if receipt.status != FiscalReceipt.STATUS_SYNCED:
                receipt.status = FiscalReceipt.STATUS_VOID
                receipt.save()
                print(f"  ✅ Receipt #{receipt_id} voided successfully")
                return True
            else:
                print(f"  ⚠️ Cannot void synced receipt #{receipt_id}")
                return False
        except FiscalReceipt.DoesNotExist:
            print(f"  ❌ Receipt #{receipt_id} not found")
            return False




    # Add this method to FiscalisationService class in fiscalisation/services.py

    def generate_receipt_signature(self, receipt: FiscalReceipt, previous_hash: str = None) -> Dict:
        """
        Generate receipt signature according to ZIMRA spec Section 13.2.1
        This is the same logic that was in device.prepareReceipt()
        """
        import hashlib
        import base64
        import os
        
        # ============================================================
        # Step 1: Build the string to sign (per spec Section 13.2.1)
        # Order: deviceID + receiptType + receiptCurrency + receiptGlobalNo + 
        #        receiptDate + receiptTotal(in cents) + receiptTaxes + previousHash
        # ============================================================
        
        # 1. deviceID
        string_to_sign = str(self.settings.device_id)
        
        # 2. receiptType (UPPER CASE)
        string_to_sign += receipt.receipt_type.upper()
        
        # 3. receiptCurrency (UPPER CASE)
        string_to_sign += receipt.currency.upper()
        
        # 4. receiptGlobalNo
        string_to_sign += str(receipt.fiscal_receipt_global_no)
        
        # 5. receiptDate (YYYY-MM-DDTHH:MM:SS)
        receipt_date_str = f"{receipt.transaction_date.strftime('%Y-%m-%d')}T{receipt.transaction_time}"
        string_to_sign += receipt_date_str
        
        # 6. receiptTotal IN CENTS (multiply by 100)
        receipt_total_cents = int(abs(receipt.total_amount) * 100)  # Use absolute value for signature
        string_to_sign += str(receipt_total_cents)
        
        # 7. receiptTaxes - concatenated: taxCode || taxPercent || taxAmount || salesAmountWithTax
        # All amounts in cents
        tax_items = []
        for tax_percent_str, tax_group in receipt.tax_breakdown.get('tax_groups', {}).items():
            tax_code = tax_group.get('tax_code', '')
            tax_percent = tax_percent_str
            tax_amount_cents = int(abs(tax_group.get('tax_amount', 0)) * 100)  # Use absolute value
            sales_amount_cents = int(abs(tax_group.get('sales_total', 0)) * 100)  # Use absolute value
            tax_items.append(f"{tax_code}{tax_percent}{tax_amount_cents}{sales_amount_cents}")
        
        # Sort taxes (required by spec)
        tax_items.sort()
        string_to_sign += ''.join(tax_items)
        
        # 8. previousReceiptHash (if exists)
        if previous_hash:
            string_to_sign += previous_hash
        
        print(f"String to sign: {string_to_sign}")
        
        # ============================================================
        # Step 2: Generate SHA256 hash
        # ============================================================
        hash_bytes = hashlib.sha256(string_to_sign.encode()).digest()
        hash_b64 = base64.b64encode(hash_bytes).decode()
        
        # ============================================================
        # Step 3: Try to sign with private key if available
        # ============================================================
        signature_b64 = hash_b64  # Default to hash if no key
        
        try:
            from fiscalisation.models import FiscalDevice
            device = FiscalDevice.objects.filter(is_active=True).first()
            if device and device.private_key_path:
                from Crypto.Signature import pkcs1_15
                from Crypto.PublicKey import RSA
                from Crypto.Hash import SHA256
                
                if os.path.exists(device.private_key_path):
                    with open(device.private_key_path, 'rb') as key_file:
                        private_key = RSA.import_key(key_file.read())
                    
                    # Sign the string
                    h = SHA256.new(string_to_sign.encode())
                    signature = pkcs1_15.new(private_key).sign(h)
                    signature_b64 = base64.b64encode(signature).decode()
                    print("Signed with private key successfully")
        except Exception as e:
            print(f"Could not sign with private key: {e}, using hash as signature")
        
        return {
            "hash": hash_b64,
            "signature": signature_b64
        }


    def generate_qr_code_from_signature(self, receipt: FiscalReceipt, signature_b64: str) -> str:
        """
        Generate QR code from signature - same as device.generate_qr_code()
        According to ZIMRA spec Section 11
        """
        import hashlib
        import base64
        
        def get_first16chars_of_signature(signature: str) -> str:
            if not isinstance(signature, str) or not signature:
                raise ValueError("Signature must be a non-empty string.")
            
            try:
                byte_array = base64.b64decode(signature)
            except (ValueError, base64.binascii.Error) as e:
                raise ValueError("Invalid Base64 string.") from e
            
            hex_str = byte_array.hex()
            md5_hash = hashlib.md5(bytes.fromhex(hex_str)).hexdigest().upper()
            return md5_hash[:16]
        
        # Get qrUrl from settings
        qr_url = self.settings.qr_url.rstrip('/') + '/'
        
        # Format components
        device_id_str = str(self.settings.device_id).zfill(10)
        receipt_date_str = receipt.transaction_date.strftime('%d%m%Y')
        receipt_global_no_str = str(receipt.fiscal_receipt_global_no).zfill(10)
        qr_data = get_first16chars_of_signature(signature_b64)
        
        # Build QR code
        qr_code = f"{qr_url}{device_id_str}{receipt_date_str}{receipt_global_no_str}{qr_data}"
        
        return qr_code