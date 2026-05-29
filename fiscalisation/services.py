# fiscalisation/services.py
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db import models
from datetime import datetime, date
from decimal import Decimal
import logging
import os
from typing import Dict, Any, Optional, List

# Import from local fixed version instead of pip package
from .zimra_client import Device, register_new_device
from .models import FiscalDevice, FiscalState, FiscalReceipt, FiscalDaySummary

logger = logging.getLogger(__name__)

class ZIMRAService:
    """Service class to handle ZIMRA FDMS operations using local client"""
    
    def __init__(self):
        self.device_instance = None
        self.mock_mode = False  # Using real client
        self._initialize_device()
    
    def _initialize_device(self):
        """Initialize device with certificates"""
        cache_key = 'zimra_device_instance'
        self.device_instance = cache.get(cache_key)
        
        if not self.device_instance:
            try:
                # Get or create fiscal device record
                fiscal_device, created = FiscalDevice.objects.get_or_create(
                    device_id=getattr(settings, 'ZIMRA_DEVICE_ID', '10626'),
                    defaults={
                        'serial_no': getattr(settings, 'ZIMRA_SERIAL_NO', '9029D38C011B'),
                        'activation_key': getattr(settings, 'ZIMRA_ACTIVATION_KEY', '00398834'),
                        'is_test_mode': getattr(settings, 'ZIMRA_TEST_MODE', True)
                    }
                )
                
                # Check if certificates exist, if not register device
                cert_path = getattr(settings, 'ZIMRA_CERT_PATH', None)
                key_path = getattr(settings, 'ZIMRA_KEY_PATH', None)
                
                if cert_path and key_path:
                    cert_dir = os.path.dirname(cert_path)
                    if not os.path.exists(cert_dir):
                        os.makedirs(cert_dir, exist_ok=True)
                    
                    if not os.path.exists(cert_path) or not os.path.exists(key_path):
                        logger.info("Certificates not found, registering device...")
                        self._register_device()
                else:
                    logger.warning("Certificate paths not configured, using mock mode")
                    self.mock_mode = True
                    return
                
                # Initialize device with local client
                self.device_instance = Device(
                    device_id=getattr(settings, 'ZIMRA_DEVICE_ID', '10626'),
                    serialNo=getattr(settings, 'ZIMRA_SERIAL_NO', '9029D38C011B'),
                    activationKey=getattr(settings, 'ZIMRA_ACTIVATION_KEY', '00398834'),
                    cert_path=cert_path,
                    private_key_path=key_path,
                    test_mode=getattr(settings, 'ZIMRA_TEST_MODE', True),
                    deviceModelName=getattr(settings, 'ZIMRA_MODEL_NAME', 'Server'),
                    deviceModelVersion=getattr(settings, 'ZIMRA_MODEL_VERSION', 'v1'),
                    company_name=getattr(settings, 'ZIMRA_COMPANY_NAME', 'ClarityPOS')
                )
                
                cache.set(cache_key, self.device_instance, 3600)
                logger.info("ZIMRA Device initialized successfully from local client")
                
            except Exception as e:
                logger.error(f"Failed to initialize ZIMRA device: {str(e)}")
                self.mock_mode = True
                logger.warning("Falling back to mock mode")
    
    def _register_device(self):
        """Register device with ZIMRA (one-time operation)"""
        try:
            folder_name = getattr(settings, 'ZIMRA_FOLDER_NAME', 'certs')
            os.makedirs(folder_name, exist_ok=True)
            
            register_new_device(
                fiscal_device_serial_no=getattr(settings, 'ZIMRA_SERIAL_NO', '9029D38C011B'),
                device_id=getattr(settings, 'ZIMRA_DEVICE_ID', '10626'),
                activation_key=getattr(settings, 'ZIMRA_ACTIVATION_KEY', '00398834'),
                model_name=getattr(settings, 'ZIMRA_MODEL_NAME', 'Server'),
                folder_name=folder_name,
                certificate_filename="certificate",
                private_key_filename="decrypted_key",
                prod=not getattr(settings, 'ZIMRA_TEST_MODE', True)
            )
            logger.info("Device registered successfully")
        except Exception as e:
            logger.error(f"Device registration failed: {str(e)}")
            raise
    
    def get_fiscal_state(self) -> FiscalState:
        """Get or create current fiscal state"""
        device_id = getattr(settings, 'ZIMRA_DEVICE_ID', '10626')
        fiscal_device, _ = FiscalDevice.objects.get_or_create(
            device_id=device_id,
            defaults={
                'serial_no': getattr(settings, 'ZIMRA_SERIAL_NO', '9029D38C011B'),
                'activation_key': getattr(settings, 'ZIMRA_ACTIVATION_KEY', '00398834'),
            }
        )
        state, created = FiscalState.objects.get_or_create(
            device=fiscal_device,
            defaults={
                'fiscal_day_no': 1,
                'receipt_counter': 1,
                'receipt_global_no': 1,
                'is_day_open': False
            }
        )
        return state
    
    def get_device_status(self) -> Dict[str, Any]:
        """Get device status from ZIMRA"""
        try:
            state = self.get_fiscal_state()
            
            # Get config from client if available
            config = {}
            status = {}
            if self.device_instance and not self.mock_mode:
                try:
                    config = self.device_instance.getConfig()
                    status = self.device_instance.getStatus()
                except Exception as e:
                    logger.warning(f"Could not get live status: {str(e)}")
            
            return {
                'success': True,
                'fiscal_day_open': state.is_day_open,
                'current_day_no': state.fiscal_day_no if not state.is_day_open else state.fiscal_day_no,
                'next_receipt_counter': state.receipt_counter,
                'next_global_no': state.receipt_global_no,
                'device_config': config,
                'device_status': status,
                'taxpayer_name': config.get('taxPayerName', 'N/A') if config else 'N/A',
                'device_serial': config.get('deviceSerialNo', getattr(settings, 'ZIMRA_SERIAL_NO', 'N/A')) if config else getattr(settings, 'ZIMRA_SERIAL_NO', 'N/A'),
                'certificate_valid_till': config.get('certificateValidTill', 'N/A') if config else 'N/A',
                'mock_mode': self.mock_mode
            }
        except Exception as e:
            logger.error(f"Failed to get device status: {str(e)}")
            return {'success': False, 'error': str(e), 'fiscal_day_open': False}
    
    def open_fiscal_day(self) -> Dict[str, Any]:
        """Open a new fiscal day"""
        state = self.get_fiscal_state()
        
        if state.is_day_open:
            return {'error': f'Fiscal day {state.fiscal_day_no} is already open', 'success': False}
        
        try:
            result = {}
            if self.device_instance and not self.mock_mode:
                result = self.device_instance.openDay(fiscalDayNo=state.fiscal_day_no)
                
                # Check for error in response
                if result.get('error'):
                    return {'error': result.get('error'), 'success': False}
            else:
                # Mock response
                result = {'operationID': f'MOCK_OPEN_{datetime.now().timestamp()}'}
            
            with transaction.atomic():
                state.is_day_open = True
                state.current_day_date = date.today()
                state.receipt_counter = 1
                state.save()
            
            logger.info(f"Opened fiscal day {state.fiscal_day_no}")
            return {
                'success': True,
                'fiscal_day_no': state.fiscal_day_no,
                'operation_id': result.get('operationID', 'N/A'),
                'message': 'Fiscal day opened successfully',
                'mock_mode': self.mock_mode
            }
        except Exception as e:
            logger.error(f"Failed to open fiscal day: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def process_receipt(self, sale_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and submit a receipt to ZIMRA"""
        state = self.get_fiscal_state()
        
        # Check if fiscal day is open
        if not state.is_day_open:
            return {'error': 'Fiscal day is not open. Please open a fiscal day first.', 'success': False}
        
        try:
            # Prepare receipt data
            receipt_data = self._build_receipt_data(sale_data, state)
            
            if self.device_instance and not self.mock_mode:
                # Prepare receipt using ZIMRA client
                prepared = self.device_instance.prepareReceipt(
                    receiptData=receipt_data,
                    previousReceiptHash=state.last_receipt_hash,
                    receiptPrintForm="Receipt48"
                )
                
                # Submit receipt
                result = self.device_instance.submitReceipt(prepared)
                
                # Check for error
                if isinstance(result, dict) and any(key for key in result.keys() if isinstance(key, int) and key >= 400):
                    error_msg = str(result)
                    return {'error': error_msg, 'success': False}
                
                # Generate QR code
                qr_url = self.device_instance.generate_qr_code(
                    signature=result.get('serverSignature', {}).get('signature', ''),
                    receipt_global_no=state.receipt_global_no,
                    receipt_date=datetime.now().date()
                )
                
                receipt_id = result.get('receiptID')
                server_signature = result.get('serverSignature')
            else:
                # Mock mode
                import hashlib
                total_amount = sum(item['unit_price'] * item['quantity'] 
                                 for item in receipt_data['receiptLines'])
                mock_signature = hashlib.sha256(
                    f"{receipt_data['invoiceNo']}{datetime.now().timestamp()}".encode()
                ).hexdigest()
                qr_url = f"https://mock.zimra.co.zw/verify/{state.receipt_global_no}/{mock_signature[:20]}"
                receipt_id = hash(f"{receipt_data['invoiceNo']}{datetime.now()}") % 1000000
                server_signature = {'signature': mock_signature, 'mock': True}
                result = {'receiptID': receipt_id, 'serverSignature': server_signature}
            
            # Save receipt record
            with transaction.atomic():
                total_amount = sum(item['unit_price'] * item['quantity'] 
                                 for item in receipt_data['receiptLines'])
                
                receipt = FiscalReceipt.objects.create(
                    fiscal_state=state,
                    receipt_global_no=state.receipt_global_no,
                    receipt_counter=state.receipt_counter,
                    receipt_type=receipt_data['receiptType'],
                    invoice_no=receipt_data['invoiceNo'],
                    receipt_id=receipt_id,
                    server_signature=server_signature,
                    total_amount=Decimal(str(total_amount)),
                    qr_code_url=qr_url
                )
                
                # Update state
                if 'hash' in locals() and not self.mock_mode:
                    state.last_receipt_hash = prepared.get('hash')
                state.receipt_counter += 1
                state.receipt_global_no += 1
                state.save()
            
            logger.info(f"Receipt submitted: Global No {state.receipt_global_no - 1}")
            
            return {
                'success': True,
                'receipt_id': receipt_id,
                'receipt_global_no': state.receipt_global_no - 1,
                'qr_code_url': qr_url,
                'server_signature': server_signature,
                'mock_mode': self.mock_mode
            }
            
        except Exception as e:
            logger.error(f"Failed to process receipt: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def _build_receipt_data(self, sale_data: Dict, state: FiscalState) -> Dict:
        """Build receipt data dictionary"""
        receipt_lines = []
        for item in sale_data['items']:
            receipt_lines.append({
                "item_name": item['name'],
                "tax_percent": item.get('tax_percent', 15.5),
                "quantity": item['quantity'],
                "unit_price": float(item['price']),
                "hs_code": item.get('hs_code', '04021099')
            })
        
        total_amount = sum(item['price'] * item['quantity'] for item in sale_data['items'])
        
        return {
            "receiptType": sale_data.get('receipt_type', 'FISCALINVOICE'),
            "receiptCurrency": sale_data.get('currency', 'USD'),
            "receiptCounter": state.receipt_counter,
            "receiptGlobalNo": state.receipt_global_no,
            "invoiceNo": sale_data['invoice_no'],
            "receiptDate": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            "receiptLines": receipt_lines,
            "receiptPayments": [
                {
                    "moneyTypeCode": sale_data.get('payment_type', 0),  # 0=Cash, 1=Card
                    "paymentAmount": float(total_amount)
                }
            ]
        }
    
    def close_fiscal_day(self, counters: Optional[List] = None) -> Dict[str, Any]:
        """Close the current fiscal day"""
        state = self.get_fiscal_state()
        
        if not state.is_day_open:
            return {'error': 'Fiscal day is not open', 'success': False}
        
        try:
            # Get receipts for the day
            receipts = FiscalReceipt.objects.filter(fiscal_state=state)
            
            if receipts.exists():
                # Build fiscal day counters from actual receipts
                fiscal_counters = self._build_day_counters(receipts)
            else:
                fiscal_counters = counters or []
            
            # Close the day with ZIMRA
            result = {}
            if self.device_instance and not self.mock_mode:
                result = self.device_instance.closeDay(
                    fiscalDayNo=state.fiscal_day_no,
                    fiscalDayDate=state.current_day_date.strftime('%Y-%m-%d') if state.current_day_date else date.today().strftime('%Y-%m-%d'),
                    lastReceiptCounterValue=state.receipt_counter - 1 if receipts.exists() else 0,
                    fiscalDayCounters=fiscal_counters
                )
                
                # Check for error
                if isinstance(result, str) and "failed" in result.lower():
                    return {'error': result, 'success': False}
            else:
                # Mock response
                result = {'status': 'MOCK_CLOSED', 'message': 'Day closed in mock mode'}
            
            # Save day summary
            with transaction.atomic():
                total_sales = receipts.aggregate(total=models.Sum('total_amount'))['total'] or 0
                
                FiscalDaySummary.objects.create(
                    fiscal_state=state,
                    fiscal_day_no=state.fiscal_day_no,
                    day_date=state.current_day_date or date.today(),
                    total_receipts=receipts.count(),
                    total_sales=total_sales,
                    closing_response=result
                )
                
                # Update state for next day
                state.is_day_open = False
                state.last_closed_day_no = state.fiscal_day_no
                state.fiscal_day_no += 1
                state.save()
            
            logger.info(f"Closed fiscal day {state.fiscal_day_no - 1}")
            
            return {
                'success': True,
                'fiscal_day_no': state.fiscal_day_no - 1,
                'total_receipts': receipts.count(),
                'total_sales': float(total_sales),
                'message': 'Fiscal day closed successfully',
                'mock_mode': self.mock_mode
            }
            
        except Exception as e:
            logger.error(f"Failed to close fiscal day: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def _build_day_counters(self, receipts):
        """Build fiscal day counters from receipts"""
        # Simplified counter builder - you'll need to expand based on your business logic
        counters = []
        
        # Group by tax rate
        tax_summary = {}
        for receipt in receipts:
            # In a real implementation, you would parse the receipt data
            # This is a placeholder
            pass
        
        # Example counter structure:
        # counters.append({
        #     "fiscalCounterType": "SaleByTax",
        #     "fiscalCounterCurrency": "USD",
        #     "fiscalCounterTaxPercent": 15.5,
        #     "fiscalCounterTaxID": 515,
        #     "fiscalCounterValue": 1000.00
        # })
        
        return counters