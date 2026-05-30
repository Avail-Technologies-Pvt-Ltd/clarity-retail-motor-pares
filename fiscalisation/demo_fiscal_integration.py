# services.py - CORRECTED VERSION (fixes global variable scope issues)
import os
import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# Import from the official zimra package
from zimra import Device, register_new_device, preprocess_receipt, tax_calculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# GLOBAL STATE (declare at module level)
# ============================================
_device_instance = None
_state = {
    'fiscal_day_no': 0,
    'receipt_counter': 0,
    'receipt_global_no': 0,
    'last_receipt_hash': None,
    'applicable_taxes': None
}


# ============================================
# INTERNAL FUNCTIONS
# ============================================

def _get_device():
    """Get or create the global device instance"""
    global _device_instance, _state  # Declare both globals at the start
    
    if _device_instance is None:
        # Load configuration from environment
        config = {
            'device_id': os.environ.get('FISCAL_DEVICE_ID', '0000000123'),
            'serial_no': os.environ.get('FISCAL_SERIAL_NO', '9029D38C011B'),
            'activation_key': os.environ.get('FISCAL_ACTIVATION_KEY', '00398834'),
            'cert_path': os.environ.get('FISCAL_CERT_PATH', 'certs/certificate.crt'),
            'private_key_path': os.environ.get('FISCAL_KEY_PATH', 'certs/decrypted_key.key'),
            'test_mode': os.environ.get('FISCAL_TEST_MODE', 'True').lower() == 'true',
            'company_name': os.environ.get('FISCAL_COMPANY_NAME', 'MyCompany'),
            'device_model_name': os.environ.get('FISCAL_MODEL_NAME', 'Server'),
            'device_model_version': os.environ.get('FISCAL_MODEL_VERSION', '1.0')
        }
        
        _device_instance = Device(
            device_id=config['device_id'],
            serialNo=config['serial_no'],
            activationKey=config['activation_key'],
            cert_path=config['cert_path'],
            private_key_path=config['private_key_path'],
            test_mode=config['test_mode'],
            deviceModelName=config['device_model_name'],
            deviceModelVersion=config['device_model_version'],
            company_name=config['company_name']
        )
        
        # Load saved state and fetch applicable taxes
        _load_state()
        _refresh_applicable_taxes()
    
    return _device_instance


def _refresh_applicable_taxes():
    """Fetch and cache applicable taxes from ZIMRA"""
    global _state  # Declare global at the start
    
    try:
        device = _get_device()
        config = device.getConfig()
        if 'applicableTaxes' in config:
            _state['applicable_taxes'] = config['applicableTaxes']
            _save_state()
            logger.info(f"Loaded {len(_state['applicable_taxes'])} applicable taxes")
    except Exception as e:
        logger.warning(f"Could not fetch applicable taxes: {e}")


def _save_state():
    """Save fiscal state to file"""
    global _state  # Declare global at the start
    
    try:
        with open('fiscal_state.json', 'w') as f:
            json.dump(_state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def _load_state():
    """Load fiscal state from file"""
    global _state  # Declare global at the start
    
    try:
        if os.path.exists('fiscal_state.json'):
            import json
            with open('fiscal_state.json', 'r') as f:
                loaded_state = json.load(f)
                _state.update(loaded_state)
                logger.info(f"Loaded state: fiscal_day={_state['fiscal_day_no']}, "
                          f"receipt_counter={_state['receipt_counter']}, "
                          f"global_no={_state['receipt_global_no']}")
    except Exception as e:
        logger.error(f"Failed to load state: {e}")


# ============================================
# PUBLIC FUNCTIONS
# ============================================

def register_device(folder_name: str = 'certs', prod: bool = False) -> bool:
    """
    Register a new device with ZIMRA (only needed once)
    
    Args:
        folder_name: Folder to save certificates
        prod: True for production, False for testing
    """
    try:
        device_id = os.environ.get('FISCAL_DEVICE_ID', '0000000123')
        serial_no = os.environ.get('FISCAL_SERIAL_NO', '9029D38C011B')
        activation_key = os.environ.get('FISCAL_ACTIVATION_KEY', '00398834')
        model_name = os.environ.get('FISCAL_MODEL_NAME', 'Server')
        
        register_new_device(
            fiscal_device_serial_no=serial_no,
            device_id=device_id,
            activation_key=activation_key,
            model_name=model_name,
            folder_name=folder_name,
            certificate_filename='certificate',
            private_key_filename='decrypted_key',
            prod=prod
        )
        logger.info(f"Device registered successfully. Certificates saved to {folder_name}/")
        return True
    except Exception as e:
        logger.error(f"Device registration failed: {e}")
        return False


def ping_device() -> bool:
    """Check if device can communicate with ZIMRA server"""
    try:
        device = _get_device()
        result = device.ping()
        if 'Error' not in result:
            logger.info("Device ping successful")
            return True
        else:
            logger.error(f"Device ping failed: {result}")
            return False
    except Exception as e:
        logger.error(f"Ping error: {e}")
        return False


def get_device_status() -> Dict:
    """Get current device status from ZIMRA"""
    global _state  # Declare global at the start
    
    try:
        device = _get_device()
        status = device.getStatus()
        if 'Error' not in status:
            _state['fiscal_day_no'] = status.get('fiscalDayNo', _state['fiscal_day_no'])
            _save_state()
        return status
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        return {'error': str(e)}


def get_device_config() -> Dict:
    """Get device configuration including applicable taxes"""
    try:
        device = _get_device()
        config = device.getConfig()
        return config
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        return {'error': str(e)}


def is_day_open() -> bool:
    """Check if fiscal day is currently open"""
    status = get_device_status()
    return status.get('fiscalDayStatus') == 'FiscalDayOpened'


def open_day(fiscal_day_no: Optional[int] = None) -> Dict:
    """Open a new fiscal day"""
    global _state  # Declare global at the start
    
    try:
        device = _get_device()
        
        # Check if day is already open
        status = get_device_status()
        if status.get('fiscalDayStatus') == 'FiscalDayOpened':
            return {'error': f"Fiscal day is already open", 'fiscalDayNo': status.get('fiscalDayNo')}
        
        # Determine next day number
        if fiscal_day_no is None:
            fiscal_day_no = status.get('lastFiscalDayNo', 0) + 1
        
        result = device.openDay(fiscal_day_no)
        
        if 'error' not in result:
            _state['fiscal_day_no'] = result.get('fiscalDayNo', fiscal_day_no)
            _state['receipt_counter'] = 0  # Reset per-day counter
            _save_state()
            logger.info(f"Fiscal day {_state['fiscal_day_no']} opened successfully")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to open day: {e}")
        return {'error': str(e)}


def fiscalise_receipt(
    items: List[Dict],
    payment_amount: float,
    invoice_no: str,
    payment_method: str = 'CASH',
    receipt_type: str = 'FISCALINVOICE',
    currency: str = 'USD',
    buyer_name: Optional[str] = None,
    buyer_tin: Optional[str] = None,
    notes: Optional[str] = None,
    tax_inclusive: bool = True,
    receipt_print_form: str = "Receipt48"
) -> Dict:
    """
    Create and submit a fiscal receipt
    
    Args:
        items: List of items with keys: name, quantity, unit_price, tax_percent
        payment_amount: Total payment amount
        invoice_no: Unique invoice number
        payment_method: 'CASH' or 'CARD' (maps to moneyTypeCode: 0=CASH, 1=CARD)
        receipt_type: 'FISCALINVOICE', 'CREDITNOTE', or 'DEBITNOTE'
        currency: 'USD' or 'ZWG'
        buyer_name: Optional buyer name
        buyer_tin: Optional buyer TIN
        notes: Optional receipt notes (REQUIRED for credit/debit notes)
        tax_inclusive: True if prices include VAT, False if prices are pre-tax
        receipt_print_form: "Receipt48" or "InvoiceA4"
    """
    global _state  # Declare global at the start
    
    try:
        device = _get_device()
        
        # Check if fiscal day is open
        if not is_day_open():
            return {'error': "Fiscal day is not open. Please open day first."}
        
        # Increment counters
        _state['receipt_counter'] += 1
        _state['receipt_global_no'] += 1
        
        # Map payment method to moneyTypeCode
        money_type_code = 0 if payment_method.upper() == 'CASH' else 1
        
        # Build receipt data
        receipt_data = {
            "receiptType": receipt_type,
            "receiptCurrency": currency,
            "receiptCounter": _state['receipt_counter'],
            "receiptGlobalNo": _state['receipt_global_no'],
            "invoiceNo": invoice_no,
            "receiptDate": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            "receiptLines": [
                {
                    "item_name": item['name'],
                    "tax_percent": float(item.get('tax_percent', 15.5)),
                    "quantity": float(item['quantity']),
                    "unit_price": float(item['unit_price']),
                    "hs_code": item.get('hs_code', '04021099')
                }
                for item in items
            ],
            "receiptPayments": [
                {
                    "moneyTypeCode": money_type_code,
                    "paymentAmount": float(payment_amount)
                }
            ]
        }
        
        # Add optional fields
        if buyer_name or buyer_tin:
            receipt_data['buyerData'] = {}
            if buyer_name:
                receipt_data['buyerData']['buyerName'] = buyer_name
            if buyer_tin:
                receipt_data['buyerData']['buyerTIN'] = buyer_tin
        
        # For credit/debit notes, notes and creditDebitNote are REQUIRED
        if receipt_type in ['CREDITNOTE', 'DEBITNOTE']:
            if not notes:
                return {'error': f"{receipt_type} requires 'notes' parameter"}
            receipt_data['receiptNotes'] = notes
        
        # Preprocess the receipt data
        if tax_inclusive:
            receipt_data = preprocess_receipt(receipt_data)
        else:
            from zimra import preprocess_tax_exclusivereceipt
            receipt_data = preprocess_tax_exclusivereceipt(receipt_data)
        
        # Prepare receipt with applicable taxes and previous hash
        prepared_receipt = device.prepareReceipt(
            receiptData=receipt_data,
            applicableTaxes=_state['applicable_taxes'],
            previousReceiptHash=_state['last_receipt_hash'],
            receiptPrintForm=receipt_print_form
        )
        
        # Submit receipt
        result = device.submitReceipt(prepared_receipt)
        
        # Check if successful
        if isinstance(result, dict) and 'receiptID' in result:
            # Store hash for next receipt
            if 'receiptDeviceSignature' in prepared_receipt:
                _state['last_receipt_hash'] = prepared_receipt['receiptDeviceSignature'].get('hash')
            _save_state()
            
            # Generate QR code using server signature from response
            qr_code = None
            if 'serverSignature' in result:
                qr_code = device.generate_qr_code(
                    signature=result['serverSignature']['signature'],
                    receipt_global_no=_state['receipt_global_no'],
                    receipt_date=datetime.now().date()
                )
            
            return {
                'success': True,
                'receipt_id': result.get('receiptID'),
                'receipt_counter': _state['receipt_counter'],
                'receipt_global_no': _state['receipt_global_no'],
                'operation_id': result.get('operationID'),
                'qr_code': qr_code,
                'server_signature': result.get('serverSignature')
            }
        else:
            # Rollback counters on failure
            _state['receipt_counter'] -= 1
            _state['receipt_global_no'] -= 1
            return {'error': str(result), 'success': False}
            
    except Exception as e:
        logger.error(f"Failed to fiscalise receipt: {e}")
        # Rollback counters on error
        _state['receipt_counter'] -= 1
        _state['receipt_global_no'] -= 1
        return {'error': str(e), 'success': False}


def close_day(fiscal_day_counters: Optional[List[Dict]] = None) -> Dict:
    """Close the current fiscal day"""
    global _state  # Declare global at the start
    
    try:
        device = _get_device()
        
        # Check if day is open
        if not is_day_open():
            return {'error': "Fiscal day is not open, cannot close"}
        
        # If no counters provided, create basic ones
        if fiscal_day_counters is None:
            fiscal_day_counters = []
        
        fiscal_day_date = datetime.now().strftime('%Y-%m-%d')
        
        result = device.closeDay(
            fiscalDayNo=_state['fiscal_day_no'],
            fiscalDayDate=fiscal_day_date,
            lastReceiptCounterValue=_state['receipt_counter'],
            fiscalDayCounters=fiscal_day_counters
        )
        
        if 'error' not in result:
            _state['receipt_counter'] = 0
            _state['last_receipt_hash'] = None
            _save_state()
            logger.info(f"Fiscal day {_state['fiscal_day_no']} closed successfully")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to close day: {e}")
        return {'error': str(e)}


def calculate_tax(amount: float, tax_rate: float = 15.5) -> float:
    """Calculate tax amount from tax-inclusive price"""
    return tax_calculator(amount, tax_rate)


def get_current_fiscal_state() -> Dict:
    """Get current fiscal state"""
    global _state  # Declare global at the start
    
    return {
        'fiscal_day_no': _state['fiscal_day_no'],
        'receipt_counter': _state['receipt_counter'],
        'receipt_global_no': _state['receipt_global_no'],
        'last_receipt_hash': _state['last_receipt_hash'],
        'is_day_open': is_day_open(),
        'applicable_taxes': _state['applicable_taxes']
    }


def reset_local_state():
    """Reset local state (use with caution)"""
    global _state  # Declare global at the start
    
    _state = {
        'fiscal_day_no': 0,
        'receipt_counter': 0,
        'receipt_global_no': 0,
        'last_receipt_hash': None,
        'applicable_taxes': None
    }
    _save_state()
    logger.warning("Local fiscal state has been reset")


# Optional: Django-style service class wrapper
class ZIMRAService:
    """Wrapper class for Django integration"""
    
    @staticmethod
    def register_device(folder_name: str = 'certs', prod: bool = False) -> bool:
        return register_device(folder_name, prod)
    
    @staticmethod
    def ping() -> bool:
        return ping_device()
    
    @staticmethod
    def get_status() -> Dict:
        return get_device_status()
    
    @staticmethod
    def get_config() -> Dict:
        return get_device_config()
    
    @staticmethod
    def is_day_open() -> bool:
        return is_day_open()
    
    @staticmethod
    def open_day(fiscal_day_no: Optional[int] = None) -> Dict:
        return open_day(fiscal_day_no)
    
    @staticmethod
    def fiscalise_receipt(
        items: List[Dict],
        payment_amount: float,
        invoice_no: str,
        payment_method: str = 'CASH',
        **kwargs
    ) -> Dict:
        return fiscalise_receipt(
            items=items,
            payment_amount=payment_amount,
            invoice_no=invoice_no,
            payment_method=payment_method,
            **kwargs
        )
    
    @staticmethod
    def close_day(fiscal_day_counters: Optional[List[Dict]] = None) -> Dict:
        return close_day(fiscal_day_counters)
    
    @staticmethod
    def calculate_tax(amount: float, tax_rate: float = 15.5) -> float:
        return calculate_tax(amount, tax_rate)
    
    @staticmethod
    def get_state() -> Dict:
        return get_current_fiscal_state()
    
    @staticmethod
    def reset_state():
        reset_local_state()