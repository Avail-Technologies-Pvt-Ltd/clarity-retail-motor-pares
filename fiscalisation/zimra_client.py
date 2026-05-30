# fiscalisation/zimra_client.py
import os
from bson import ObjectId
import requests
import datetime
import logging
from datetime import datetime
import json
import hashlib
import base64
from collections import OrderedDict, defaultdict
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from Crypto.Signature import pkcs1_15
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from cryptography.hazmat.primitives.asymmetric import rsa

logging.basicConfig(level=logging.INFO)

__all__ = [
    'register_new_device',
    'tax_calculator',
    'Device',
    'ZimraServerError'
]


class ZimraServerError(Exception):
    """Raised when the Zimra server returns an error."""
    
    def __init__(self, status_code, message):
        self.status_code = status_code
        super().__init__(f"ZimraServerError {status_code}: {message}")

def convert_objectid_to_str(data):
    if isinstance(data, dict):
        return {k: str(v) if isinstance(v, ObjectId) else v for k, v in data.items()}
    return data

def register_new_device(
    fiscal_device_serial_no: str, 
    device_id: str,
    activation_key: str, 
    model_name: str = 'Server',
    folder_name: str = 'prod', 
    certificate_filename: str = 'certificate', 
    private_key_filename: str = 'decrypted_key',
    prod: bool = False
):
    """Register a new device with ZIMRA"""
    if not os.path.exists(f'{folder_name}'):
        os.makedirs(f'{folder_name}')

    formatted_device_id = device_id.zfill(10)

    # Generate RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Save private key
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    with open(f"{folder_name}/{private_key_filename}.key", "wb") as key_file:
        key_file.write(private_key_pem)
        logging.info(f"Private key saved to {folder_name}/{private_key_filename}.key")

    common_name = f'ZIMRA-{fiscal_device_serial_no}-{formatted_device_id}'

    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])).sign(private_key, hashes.SHA256(), default_backend())

    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode('utf-8')
    
    if prod:
        url = f'https://fdmsapi.zimra.co.zw/Public/v1/{device_id}/RegisterDevice'
    else:
        url = f'https://fdmsapitest.zimra.co.zw/Public/v1/{device_id}/RegisterDevice'

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'DeviceModelName': model_name,
        'DeviceModelVersion': '1.0'
    }

    payload = {
        'activationKey': activation_key,
        'certificateRequest': csr_pem,
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        logging.info("Request was successful!")
        response_json = response.json()
        certificate_pem = response_json['certificate']

        with open(f"{folder_name}/{certificate_filename}.crt", "w") as cert_file:
            cert_file.write(certificate_pem)
            logging.info(f"Certificate saved to {folder_name}/{certificate_filename}.crt")
    else:
        logging.fatal(f"Request failed with status code {response.status_code}")
        logging.critical(response.text)

def tax_calculator(sale_amount, tax_rate):
    tax_rate = (tax_rate / 100)
    tax_amount = round(((sale_amount * tax_rate) / (1 + tax_rate)), 2)
    return tax_amount

class Device:
    def __init__(
            self,
            device_id: str, 
            serialNo: str, 
            activationKey: str, 
            cert_path: str, 
            private_key_path: str, 
            test_mode: bool = True, 
            deviceModelName: str = 'Model123', 
            deviceModelVersion: str = '1.0',
            company_name: str = "NexusClient"
        ):
        self.companyName: str = company_name
        self.deviceID: int = device_id
        self.deviceModelName = deviceModelName
        self.deviceModelVersion = deviceModelVersion
        self.certPath: str = cert_path
        self.keyPath: str = private_key_path
        
        if test_mode:
            self.base_url: str = 'https://fdmsapitest.zimra.co.zw/Device/v1/'
            self.qrUrl: str = 'https://fdmstest.zimra.co.zw/'
        else:
            self.base_url: str = 'https://fdmsapi.zimra.co.zw/Device/v1/'
            self.qrUrl: str = 'https://fdms.zimra.co.zw/'

        self.deviceBaseUrl = f'{self.base_url}{self.deviceID}'
        self.serialNo = serialNo
        self.activationKey = activationKey

    def tax_calculator(self, sale_amount: float, tax_rate: int) -> float:
        tax_rate = (tax_rate / 100)
        tax_amount = round(((sale_amount * tax_rate) / (1 + tax_rate)), 2)
        return tax_amount
    
    def concatenate_receipt_taxes(self, receiptTaxes):
        receiptTaxes_sorted = sorted(receiptTaxes, key=lambda x: (x['taxID']))
        concatenated_string = ''.join(
            f"{float(tax['taxPercent']):.2f}{int(tax['taxAmount']*100)}{int(tax['salesAmountWithTax']*100)}" 
            for tax in receiptTaxes_sorted
        )
        return concatenated_string

    def get_hash(self, data: str) -> str:
        hash_object = hashlib.sha256(data.encode('utf-8'))
        return base64.b64encode(hash_object.digest()).decode('utf-8')
    
    def sign_data(self, data: str) -> str:
        with open(self.keyPath, 'rb') as key_file:
            private_key_pem = key_file.read()
        key = RSA.import_key(private_key_pem)
        h = SHA256.new(data.encode('utf-8'))
        signature = pkcs1_15.new(key).sign(h)
        return base64.b64encode(signature).decode('utf-8')
    
    def getConfig(self) -> dict:
        url = f'{self.deviceBaseUrl}/GetConfig'
        response = requests.get(
            url,
            cert=(self.certPath, self.keyPath),
            headers={
                'DeviceModelName': self.deviceModelName,
                'DeviceModelVersion': self.deviceModelVersion
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"Error": f"Error: {response.status_code} - {response.text}"}

    def renewCertificate(self):
        device_id = self.deviceID
        serial_no = self.serialNo
        device_id_padded = str(device_id).zfill(10)
        cn_value = f"ZIMRA-{serial_no}-{device_id_padded}"

        with open(self.keyPath, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
                backend=default_backend()
            )

        csr_builder = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, cn_value),
        ]))

        csr = csr_builder.sign(private_key, hashes.SHA256(), default_backend())
        csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode('utf-8')

        url = f'{self.deviceBaseUrl}/IssueCertificate'
        headers = {
            'DeviceModelName': self.deviceModelName,
            'DeviceModelVersion': self.deviceModelVersion,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        data = {"certificateRequest": csr_pem}

        try:
            response = requests.post(
                url,
                headers=headers,
                cert=(self.certPath, self.keyPath),
                json=data,
            )
            response.raise_for_status()
            with open(f'{self.companyName}.crt', 'w') as cert_file:
                cert_file.write(response.json()['certificate'])
            return response.json()['certificate']
        except requests.exceptions.HTTPError as http_err:
            error_response = response.json()
            return f"HTTP error occurred: {http_err}\n\nResponse: {error_response}"
        except Exception as err:
            return f"Other error occurred: {err}"

    def getStatus(self) -> dict:
        url = f'{self.deviceBaseUrl}/GetStatus'
        response = requests.get(
            url,
            cert=(self.certPath, self.keyPath),
            headers={
                'DeviceModelName': self.deviceModelName,
                'DeviceModelVersion': self.deviceModelVersion
            }
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"Error": f"Error: {response.status_code} - {response.text}"}

    def ping(self) -> dict:
        url = f'{self.deviceBaseUrl}/Ping'
        headers = {
            'DeviceModelName': self.deviceModelName,
            'DeviceModelVersion': self.deviceModelVersion,
            'accept': 'application/json',
        }
        response = requests.post(
            url,
            cert=(self.certPath, self.keyPath),
            headers=headers
        )
        if response.status_code == 200:
            logging.info("PING was successful!")
            return response.json()
        else:
            return {"Error": f"{response.text}"}

    def openDay(self, fiscalDayNo: int) -> dict:
        fiscalDayOpened = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        status = self.getStatus()
        
        if status.get('fiscalDayStatus') != 'FiscalDayClosed':
            return {"error": f"Fiscal Day {status.get('lastFiscalDayNo', 'unknown')} is not closed"}
        
        if fiscalDayNo <= status.get('lastFiscalDayNo', 0):
            return {"error": f"Fiscal Day being opened: day {fiscalDayNo} is earlier than the last closed day: day {status['lastFiscalDayNo']}"}
        
        url = f'{self.deviceBaseUrl}/OpenDay'
        headers = {
            'DeviceModelName': self.deviceModelName,
            'DeviceModelVersion': self.deviceModelVersion,
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        payload = {
            "fiscalDayNo": fiscalDayNo,
            "fiscalDayOpened": fiscalDayOpened
        }
        
        try:
            response = requests.post(
                url,
                cert=(self.certPath, self.keyPath),
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"HTTP request failed: {e}"}
        except ValueError:
            return {"error": "Invalid JSON response"}

    def prepareReceipt(self, receiptData: dict, previousReceiptHash=None, receiptPrintForm="Receipt48") -> dict:
        """Prepare a receipt for submission - FIXED VERSION with correct f-string syntax"""
        
        def receiptlinesfixer(receipt: dict) -> dict:
            def taxID(line):
                tax_percent = float(line['tax_percent'])
                if int(tax_percent) == 0:
                    return 2
                elif tax_percent == 5:
                    return 1
                elif tax_percent == 15:
                    return 3
                else:
                    raise ValueError(f"Invalid tax_percent value: {tax_percent}")
                
            receiptlines = receipt['receiptLines']
            output_receipt_lines = []

            for i, line in enumerate(receiptlines):
                fixed_line = {
                    'receiptLineType': 'Sale',
                    'receiptLineNo': i + 1,
                    'receiptLineHSCode': '04021099' if 'hs_code' not in line else line['hs_code'],
                    'receiptLineName': line['item_name'],
                    'receiptLinePrice': line['unit_price'],
                    'receiptLineQuantity': line['quantity'],
                    'receiptLineTotal': float(line['quantity']) * float(line['unit_price']),
                    'taxPercent': line['tax_percent'],
                    'taxID': taxID(line)
                }
                output_receipt_lines.append(fixed_line)
                
            receipt["receiptLines"] = output_receipt_lines
            return receipt

        def taxlines_fixer(receipt: OrderedDict) -> OrderedDict:
            receipt_with_taxlines = OrderedDict()
            for key, value in receipt.items():
                receipt_with_taxlines[key] = value
                if key == "receiptLines":
                    tax_lines = defaultdict(lambda: {"taxAmount": 0, "salesAmountWithTax": 0})
                    for item in receipt["receiptLines"]:
                        tax_percent = round(float(item["taxPercent"]), 2)
                        tax_id = int(item["taxID"])
                        tax_lines[(tax_percent, tax_id)]["taxAmount"] += self.tax_calculator(item["receiptLineTotal"], tax_percent)
                        tax_lines[(tax_percent, tax_id)]["salesAmountWithTax"] += item["receiptLineTotal"]
                        tax_lines[(tax_percent, tax_id)]["taxPercent"] = tax_percent
                        tax_lines[(tax_percent, tax_id)]["taxID"] = tax_id
                    receipt_with_taxlines["receiptTaxes"] = [
                        {
                            "taxPercent": float("{:.2f}".format(float(key[0]))),
                            "taxID": key[1],
                            "taxAmount": self.tax_calculator(sale_amount=value["salesAmountWithTax"], tax_rate=float("{:.2f}".format(float(key[0])))),
                            "salesAmountWithTax": value["salesAmountWithTax"]
                        }
                        for key, value in tax_lines.items()
                    ]
            return receipt_with_taxlines

        # CRITICAL FIX: Changed double quotes to single quotes inside f-strings
        def insert_receiptDeviceSignature(receiptData: OrderedDict, previous_hash=previousReceiptHash) -> OrderedDict:
            receiptTaxes = receiptData["receiptTaxes"]
            concatenated_receipt_taxes = self.concatenate_receipt_taxes(receiptTaxes=receiptTaxes)
            
            if previous_hash:
                # FIXED: Using single quotes inside f-string
                string_to_sign = f"{self.deviceID}{receiptData['receiptType'].upper()}{receiptData['receiptCurrency'].upper()}{receiptData['receiptGlobalNo']}{receiptData['receiptDate']}{int(receiptData['receiptTotal']*100)}{concatenated_receipt_taxes}{previous_hash}"
                logging.info(f"Library Info: string to sign: {string_to_sign}")
            else:
                # FIXED: Using single quotes inside f-string
                string_to_sign = f"{self.deviceID}{receiptData['receiptType'].upper()}{receiptData['receiptCurrency'].upper()}{receiptData['receiptGlobalNo']}{receiptData['receiptDate']}{int(receiptData['receiptTotal']*100)}{concatenated_receipt_taxes}"
                logging.info(f"Library Info: string to sign: {string_to_sign}")
                
            hash_value = self.get_hash(string_to_sign)
            signature = self.sign_data(string_to_sign)
            receiptData["receiptDeviceSignature"] = {
                "hash": hash_value,
                "signature": signature
            }
            return receiptData
        
        # Mandatory fields
        mandatory_fields = [
            "receiptType", "receiptCurrency", "receiptCounter", "receiptGlobalNo",
            "invoiceNo", "receiptDate", "receiptLines", "receiptPayments",
        ]

        optional_fields = ["buyerData", "creditDebitNote", "receiptNotes"]

        prepared_receipt = OrderedDict()
        if receiptData['receiptType'].lower() in ['creditnote', 'debitnote']:
            mandatory_fields.append('receiptNotes')
            mandatory_fields.append('creditDebitNote')
        
        for field in mandatory_fields:
            if field not in receiptData:
                raise ValueError(f"Library Error: Missing mandatory field: {field}")
            prepared_receipt[field] = receiptData[field]

        # Format receiptDate
        if isinstance(prepared_receipt['receiptDate'], datetime):
            prepared_receipt['receiptDate'] = prepared_receipt['receiptDate'].strftime('%Y-%m-%dT%H:%M:%S')
        elif isinstance(prepared_receipt['receiptDate'], str):
            try:
                prepared_receipt['receiptDate'] = datetime.strptime(prepared_receipt['receiptDate'], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')
            except ValueError:
                try:
                    prepared_receipt['receiptDate'] = datetime.strptime(prepared_receipt['receiptDate'][:-5], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')
                    logging.info(f"Library Info: Manually formatted date: {prepared_receipt['receiptDate']}")
                except ValueError:
                    raise ValueError("Library Error: Invalid receiptDate format")
        else:
            raise ValueError("Library Error: Invalid receiptDate format")

        prepared_receipt['receiptLinesTaxInclusive'] = True
        prepared_receipt['receiptTotal'] = sum([float(line['unit_price']) * float(line['quantity']) for line in receiptData['receiptLines']])

        for field in optional_fields:
            if field in receiptData:
                prepared_receipt[field] = receiptData[field]

        # Process the receipt
        reordered_receipt = OrderedDict()
        for key in list(prepared_receipt.keys()):
            reordered_receipt[key] = prepared_receipt[key]
            if key == "receiptDate":
                reordered_receipt["receiptLinesTaxInclusive"] = True
                
        reordered_receipt = receiptlinesfixer(reordered_receipt)
        reordered_receipt = taxlines_fixer(receipt=reordered_receipt)
        
        if reordered_receipt['receiptTotal'] != reordered_receipt['receiptPayments'][0]['paymentAmount']:
            logging.info(f"Library Error: Receipt total ({reordered_receipt['receiptTotal']}) does not match payment amount. Fixing...")
            reordered_receipt['receiptTotal'] = float(reordered_receipt['receiptPayments'][0]['paymentAmount'])
            
        reordered_receipt = insert_receiptDeviceSignature(receiptData=reordered_receipt)
        reordered_receipt['receiptPrintForm'] = receiptPrintForm
        
        return reordered_receipt

    def submitReceipt(self, receiptData: dict) -> dict:
        url = f'{self.deviceBaseUrl}/SubmitReceipt'
        headers = {
            'DeviceModelName': self.deviceModelName,
            'DeviceModelVersion': self.deviceModelVersion,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        fields = [
            "receiptType", "receiptCurrency", "receiptCounter", "receiptGlobalNo",
            "invoiceNo", "buyerData", "receiptNotes", "receiptDate", "creditDebitNote",
            "receiptLinesTaxInclusive", "receiptLines", "receiptTaxes", "receiptPayments",
            "receiptTotal", "receiptPrintForm", "receiptDeviceSignature"
        ]

        payload = {"Receipt": {key: receiptData[key] for key in fields if key in receiptData}}
        logging.info(f"==== RECEIPT SENT\n\n{json.dumps(payload, indent=4)}")

        response = requests.post(
            url,
            cert=(self.certPath, self.keyPath),
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {response.status_code: response.text}

    def generate_qr_code(self, signature: str, receipt_global_no, receipt_date=datetime.now().date()):
        def get_first16chars_of_signature(signature: str) -> str:
            if not isinstance(signature, str) or not signature:
                raise ValueError("Input must be a non-empty string.")
            try:
                byte_array = base64.b64decode(signature)
            except (ValueError, base64.binascii.Error) as e:
                raise ValueError("Invalid Base64 string.") from e
            hex_str = byte_array.hex()
            md5_hash = hashlib.md5(bytes.fromhex(hex_str)).hexdigest()
            return md5_hash[:16]

        def generate_qr_code_string(device_id, receipt_date, receipt_global_no, receipt_device_signature, qr_url):
            device_id = str(self.deviceID).zfill(10)
            receipt_date = receipt_date.strftime('%d%m%Y')
            receipt_global_no = str(receipt_global_no).zfill(10)
            md5_hash = receipt_device_signature
            qr_value = f"{qr_url}{device_id}{receipt_date}{receipt_global_no}{md5_hash}"
            return qr_value

        receipt_device_signature = get_first16chars_of_signature(signature)
        qr_code_value = generate_qr_code_string(
            device_id=self.deviceID,
            receipt_date=receipt_date,
            receipt_global_no=receipt_global_no,
            receipt_device_signature=receipt_device_signature,
            qr_url=self.qrUrl
        )
        return qr_code_value

    def closeDay(self, fiscalDayNo: int, fiscalDayDate, lastReceiptCounterValue: int, fiscalDayCounters: list):
        if lastReceiptCounterValue is None or fiscalDayCounters is None or fiscalDayCounters == []:
            lastReceiptCounterValue = 0
            string_to_implement = f'{self.deviceID}{fiscalDayNo}{fiscalDayDate}'
        
        def generate_string(device_id, fiscal_day_no, fiscal_day_date, fiscal_day_counters):
            money_type_mapping = {0: "CASH", 1: "CARD"}
            sorted_counters = sorted(
                fiscal_day_counters,
                key=lambda x: (
                    1 if x['fiscalCounterType'] == 'SaleByTax' else
                    2 if x['fiscalCounterType'] == 'SaleTaxByTax' else
                    3 if x['fiscalCounterType'] == 'CreditNoteByTax' else
                    4 if x['fiscalCounterType'] == 'CreditNoteTaxByTax' else
                    5 if x['fiscalCounterType'] == 'DebitNoteByTax' else
                    6 if x['fiscalCounterType'] == 'DebitNoteTaxByTax' else
                    7 if x['fiscalCounterType'] == 'BalanceByMoneyType' else 99,
                    x['fiscalCounterCurrency'],
                    x.get('fiscalCounterTaxID', ''),
                    x.get('fiscalCounterMoneyType', '')
                )
            )
            concatenated_counters = ''.join(
                f"{counter['fiscalCounterType'].upper()}"
                f"{counter['fiscalCounterCurrency'].upper()}"
                f"{'{:.2f}'.format(counter['fiscalCounterTaxPercent']) if counter.get('fiscalCounterTaxPercent') is not None else ''}"
                f"{money_type_mapping.get(counter.get('fiscalCounterMoneyType'), '')}"
                f"{int(float(counter['fiscalCounterValue']) * 100)}"
                for counter in sorted_counters
                if float(counter['fiscalCounterValue']) != float(0)
            )
            logging.info(f"Concatenated Counters: {concatenated_counters}")
            string_to_implement = f"{device_id}{fiscal_day_no}{fiscal_day_date}{concatenated_counters}"
            return string_to_implement

        fiscalDayCounters = convert_objectid_to_str(fiscalDayCounters)
        if fiscalDayCounters != []:
            string_to_implement = generate_string(self.deviceID, fiscalDayNo, fiscalDayDate, fiscalDayCounters)
        else:
            string_to_implement = f'{self.deviceID}{fiscalDayNo}{fiscalDayDate}'
        
        logging.info(f"STRING TO IMPLEMENT CLOSE DAY: {string_to_implement}")
        hash_value = self.get_hash(string_to_implement)
        
        with open(self.keyPath, 'rb') as key_file:
            private_key_pem = key_file.read()
        fDSSignature = self.sign_data(string_to_implement)
        
        url = f'{self.deviceBaseUrl}/CloseDay'
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        if hasattr(self, 'deviceModelName'):
            headers['DeviceModelName'] = self.deviceModelName
        if hasattr(self, 'deviceModelVersion'):
            headers['DeviceModelVersion'] = self.deviceModelVersion

        payload = {
            "deviceID": self.deviceID,
            "fiscalDayNo": fiscalDayNo,
            "fiscalDayCounters": fiscalDayCounters,
            "fiscalDayDeviceSignature": {
                "hash": hash_value,
                "signature": fDSSignature
            },
            "receiptCounter": lastReceiptCounterValue
        }

        logging.info(f"CLOSE DAY Payload: {payload}")

        try:
            response = requests.post(
                url,
                headers=headers,
                cert=(self.certPath, self.keyPath),
                json=payload
            )
            logging.info(f"Response from Zimra: {response.json()}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return f"HTTP request failed: {e}"
        except ValueError:
            return f"Invalid JSON response"