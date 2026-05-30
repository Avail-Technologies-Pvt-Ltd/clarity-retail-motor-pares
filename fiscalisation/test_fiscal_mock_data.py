# demo_fiscal_integration.py
"""
Demo script for testing the fiscal device integration with mock data
Run this to test all functionality before integrating with your POS
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random

# Add the current directory to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our fiscal services
from services import (
    register_device,
    ping_device,
    get_device_status,
    get_device_config,
    open_day,
    close_day,
    fiscalise_receipt,
    calculate_tax,
    get_current_fiscal_state,
    is_day_open,
    reset_local_state
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# MOCK DATA GENERATORS
# ============================================

class MockDataGenerator:
    """Generate mock sales data for testing"""
    
    # Product catalog
    PRODUCTS = {
        'Laptop': {'price': 1155.00, 'tax': 15.5, 'hs_code': '84713010'},
        'Mouse': {'price': 23.10, 'tax': 15.5, 'hs_code': '84716000'},
        'Keyboard': {'price': 46.20, 'tax': 15.5, 'hs_code': '84716000'},
        'Monitor': {'price': 346.50, 'tax': 15.5, 'hs_code': '85285210'},
        'USB Cable': {'price': 11.55, 'tax': 15.5, 'hs_code': '85444290'},
        'Printer': {'price': 231.00, 'tax': 15.5, 'hs_code': '84433210'},
        'External HDD': {'price': 92.40, 'tax': 15.5, 'hs_code': '84717050'},
        'Mouse Pad': {'price': 5.78, 'tax': 0, 'hs_code': '42029200'},  # Zero-rated
        'Donation': {'price': 10.00, 'tax': 'exempt', 'hs_code': '99999999'},  # Exempt
        'Software License': {'price': 500.00, 'tax': 15.5, 'hs_code': '85234910'}
    }
    
    # Buyer database (mock)
    BUYERS = [
        {'name': 'John Doe', 'tin': '1234567890'},
        {'name': 'Jane Smith', 'tin': '0987654321'},
        {'name': 'ABC Corporation', 'tin': '1122334455'},
        {'name': 'XYZ Enterprises', 'tin': '5544332211'},
        {'name': 'Retail Store Ltd', 'tin': '9988776655'},
        None  # No buyer info (walk-in customer)
    ]
    
    @classmethod
    def generate_random_items(cls, min_items: int = 1, max_items: int = 5) -> List[Dict]:
        """Generate random list of items"""
        num_items = random.randint(min_items, max_items)
        items = []
        product_names = list(cls.PRODUCTS.keys())
        
        for _ in range(num_items):
            product = random.choice(product_names)
            product_info = cls.PRODUCTS[product]
            quantity = random.randint(1, 3)
            
            items.append({
                'name': product,
                'quantity': quantity,
                'unit_price': product_info['price'],
                'tax_percent': product_info['tax'],
                'hs_code': product_info['hs_code']
            })
        
        return items
    
    @classmethod
    def calculate_total(cls, items: List[Dict]) -> float:
        """Calculate total amount from items"""
        total = sum(item['quantity'] * item['unit_price'] for item in items)
        return round(total, 2)
    
    @classmethod
    def get_random_buyer(cls) -> Dict:
        """Get random buyer info"""
        buyer = random.choice(cls.BUYERS)
        return buyer if buyer else None
    
    @classmethod
    def generate_receipt_data(cls, include_buyer: bool = True) -> Dict:
        """Generate complete receipt data"""
        items = cls.generate_random_items()
        total = cls.calculate_total(items)
        buyer = cls.get_random_buyer() if include_buyer else None
        
        receipt_data = {
            'items': items,
            'payment_amount': total,
            'invoice_no': f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}",
            'payment_method': random.choice(['CASH', 'CARD']),
            'receipt_type': 'FISCALINVOICE',
            'currency': 'USD',
            'tax_inclusive': True,
            'receipt_print_form': random.choice(['Receipt48', 'InvoiceA4'])
        }
        
        if buyer:
            receipt_data['buyer_name'] = buyer['name']
            receipt_data['buyer_tin'] = buyer['tin']
        
        return receipt_data
    
    @classmethod
    def generate_day_counters(cls, receipts_submitted: List[Dict]) -> List[Dict]:
        """Generate fiscal day counters from submitted receipts"""
        counters = []
        
        # Aggregate sales by tax rate
        sales_by_tax = {}
        taxes_by_tax = {}
        
        for receipt in receipts_submitted:
            for item in receipt.get('items', []):
                tax_rate = item['tax_percent']
                if tax_rate not in sales_by_tax:
                    sales_by_tax[tax_rate] = 0
                    taxes_by_tax[tax_rate] = 0
                
                item_total = item['quantity'] * item['unit_price']
                sales_by_tax[tax_rate] += item_total
                
                # Calculate tax amount
                if tax_rate != 'exempt' and tax_rate != 0:
                    tax_amount = calculate_tax(item_total, float(tax_rate))
                    taxes_by_tax[tax_rate] += tax_amount
        
        # Add SaleByTax counters
        for tax_rate, total in sales_by_tax.items():
            if total > 0:
                # Get tax ID (simplified mapping)
                tax_id = 515 if tax_rate == 15.5 else 514 if tax_rate == 5 else 2
                
                counters.append({
                    "fiscalCounterType": "SaleByTax",
                    "fiscalCounterCurrency": "USD",
                    "fiscalCounterTaxPercent": float(tax_rate) if tax_rate != 'exempt' else 0,
                    "fiscalCounterTaxID": tax_id,
                    "fiscalCounterValue": round(total, 2)
                })
        
        # Add SaleTaxByTax counters
        for tax_rate, tax_amount in taxes_by_tax.items():
            if tax_amount > 0:
                tax_id = 515 if tax_rate == 15.5 else 514 if tax_rate == 5 else 2
                counters.append({
                    "fiscalCounterType": "SaleTaxByTax",
                    "fiscalCounterCurrency": "USD",
                    "fiscalCounterTaxPercent": float(tax_rate),
                    "fiscalCounterTaxID": tax_id,
                    "fiscalCounterValue": round(tax_amount, 2)
                })
        
        # Add BalanceByMoneyType counter
        total_sales = sum(sales_by_tax.values())
        if total_sales > 0:
            counters.append({
                "fiscalCounterType": "BalanceByMoneyType",
                "fiscalCounterCurrency": "USD",
                "fiscalCounterMoneyType": 0,  # Cash
                "fiscalCounterValue": round(total_sales, 2)
            })
        
        return counters

# ============================================
# TEST FUNCTIONS
# ============================================

def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_dict(data: Dict, indent: int = 2):
    """Pretty print a dictionary"""
    print(json.dumps(data, indent=indent, default=str))

def test_initial_setup():
    """Test device registration and configuration"""
    print_section("1. INITIAL SETUP & REGISTRATION")
    
    # Check if certificates already exist
    cert_path = os.environ.get('FISCAL_CERT_PATH', 'certs/certificate.crt')
    
    if not os.path.exists(cert_path):
        print("📝 Certificates not found. Registering new device...")
        success = register_device(folder_name='certs', prod=False)
        if success:
            print("✅ Device registered successfully!")
        else:
            print("❌ Device registration failed!")
            return False
    else:
        print("✅ Certificates already exist. Skipping registration.")
    
    # Test ping
    print("\n📡 Testing connection to ZIMRA server...")
    if ping_device():
        print("✅ Connection successful!")
    else:
        print("❌ Connection failed!")
        return False
    
    # Get device configuration
    print("\n⚙️ Fetching device configuration...")
    config = get_device_config()
    if 'error' not in config:
        print("✅ Configuration retrieved!")
        print(f"   Taxpayer: {config.get('taxPayerName')}")
        print(f"   TIN: {config.get('taxPayerTIN')}")
        print(f"   Certificate valid till: {config.get('certificateValidTill')}")
        
        # Display applicable taxes
        taxes = config.get('applicableTaxes', [])
        print(f"\n   Applicable Taxes ({len(taxes)}):")
        for tax in taxes:
            tax_percent = tax.get('taxPercent', 'N/A')
            tax_name = tax.get('taxName', 'Unknown')
            print(f"     - {tax_name}: {tax_percent}%")
    else:
        print(f"❌ Failed to get config: {config.get('error')}")
    
    return True

def test_fiscal_day_operations():
    """Test opening and closing fiscal days"""
    print_section("2. FISCAL DAY OPERATIONS")
    
    # Get current state
    state = get_current_fiscal_state()
    print(f"📊 Current fiscal state:")
    print(f"   Day number: {state['fiscal_day_no']}")
    print(f"   Day open: {state['is_day_open']}")
    print(f"   Receipt counter: {state['receipt_counter']}")
    
    # Open day if closed
    if not state['is_day_open']:
        print("\n🔓 Opening new fiscal day...")
        result = open_day()
        if 'error' in result:
            print(f"❌ Failed to open day: {result['error']}")
            return False
        else:
            print(f"✅ Fiscal day opened!")
            print(f"   Day number: {result.get('fiscalDayNo')}")
            print(f"   Operation ID: {result.get('operationID')}")
    else:
        print(f"\n✅ Fiscal day is already open (Day {state['fiscal_day_no']})")
    
    return True

def test_single_receipt():
    """Test fiscalising a single receipt"""
    print_section("3. SINGLE RECEIPT FISCALISATION")
    
    # Generate mock receipt data
    receipt_data = MockDataGenerator.generate_receipt_data(include_buyer=True)
    
    print("📝 Receipt data:")
    print(f"   Invoice: {receipt_data['invoice_no']}")
    print(f"   Items: {len(receipt_data['items'])}")
    for item in receipt_data['items']:
        print(f"     - {item['name']}: {item['quantity']} x ${item['unit_price']:.2f} ({item['tax_percent']}% tax)")
    print(f"   Total: ${receipt_data['payment_amount']:.2f}")
    print(f"   Payment: {receipt_data['payment_method']}")
    if receipt_data.get('buyer_name'):
        print(f"   Buyer: {receipt_data['buyer_name']} (TIN: {receipt_data.get('buyer_tin')})")
    
    # Submit receipt
    print("\n📤 Submitting to ZIMRA...")
    result = fiscalise_receipt(
        items=receipt_data['items'],
        payment_amount=receipt_data['payment_amount'],
        invoice_no=receipt_data['invoice_no'],
        payment_method=receipt_data['payment_method'],
        receipt_type=receipt_data['receipt_type'],
        currency=receipt_data['currency'],
        buyer_name=receipt_data.get('buyer_name'),
        buyer_tin=receipt_data.get('buyer_tin'),
        tax_inclusive=receipt_data['tax_inclusive'],
        receipt_print_form=receipt_data['receipt_print_form']
    )
    
    if result.get('success'):
        print("✅ Receipt fiscalised successfully!")
        print(f"   Receipt ID: {result['receipt_id']}")
        print(f"   Receipt #: {result['receipt_counter']}")
        print(f"   Global #: {result['receipt_global_no']}")
        print(f"   QR Code URL: {result['qr_code']}")
        return result
    else:
        print(f"❌ Failed to fiscalise receipt: {result.get('error')}")
        return None

def test_multiple_receipts(num_receipts: int = 3):
    """Test fiscalising multiple receipts"""
    print_section(f"4. MULTIPLE RECEIPTS ({num_receipts} receipts)")
    
    receipts_submitted = []
    
    for i in range(num_receipts):
        print(f"\n--- Receipt {i+1} of {num_receipts} ---")
        
        # Generate different types of receipts
        if i == 0:
            # Regular receipt with buyer
            receipt_data = MockDataGenerator.generate_receipt_data(include_buyer=True)
        elif i == 1:
            # Receipt with multiple items
            receipt_data = MockDataGenerator.generate_receipt_data(include_buyer=True)
            receipt_data['items'] = MockDataGenerator.generate_random_items(min_items=3, max_items=6)
            receipt_data['payment_amount'] = MockDataGenerator.calculate_total(receipt_data['items'])
        else:
            # Receipt with cash sale (no buyer)
            receipt_data = MockDataGenerator.generate_receipt_data(include_buyer=False)
        
        print(f"   Invoice: {receipt_data['invoice_no']}")
        print(f"   Items: {len(receipt_data['items'])}")
        print(f"   Total: ${receipt_data['payment_amount']:.2f}")
        
        result = fiscalise_receipt(
            items=receipt_data['items'],
            payment_amount=receipt_data['payment_amount'],
            invoice_no=receipt_data['invoice_no'],
            payment_method=receipt_data['payment_method'],
            buyer_name=receipt_data.get('buyer_name'),
            buyer_tin=receipt_data.get('buyer_tin'),
            tax_inclusive=receipt_data['tax_inclusive']
        )
        
        if result.get('success'):
            print(f"   ✅ Success! Receipt #{result['receipt_counter']}")
            receipts_submitted.append({
                'receipt_data': receipt_data,
                'result': result
            })
        else:
            print(f"   ❌ Failed: {result.get('error')}")
    
    print(f"\n📊 Summary: {len(receipts_submitted)} of {num_receipts} receipts successful")
    return receipts_submitted

def test_tax_calculations():
    """Test tax calculation accuracy"""
    print_section("5. TAX CALCULATIONS")
    
    test_cases = [
        {'amount': 115.50, 'rate': 15.5, 'expected_tax': 15.50},
        {'amount': 100.00, 'rate': 15.5, 'expected_tax': 13.42},
        {'amount': 50.00, 'rate': 5, 'expected_tax': 2.38},
        {'amount': 25.00, 'rate': 0, 'expected_tax': 0.00},
        {'amount': 1000.00, 'rate': 15.5, 'expected_tax': 134.20},
    ]
    
    print("Testing tax calculations (tax-inclusive to tax amount):")
    print(f"{'Amount':<12} {'Rate':<8} {'Calculated Tax':<15} {'Expected':<12} {'Status'}")
    print("-" * 55)
    
    for test in test_cases:
        calculated = calculate_tax(test['amount'], test['rate'])
        status = "✅" if abs(calculated - test['expected_tax']) < 0.01 else "❌"
        print(f"${test['amount']:<10} {test['rate']}%{'':<4} ${calculated:<13.2f} ${test['expected_tax']:<10} {status}")
    
    # Test on a sample receipt
    items = [
        {'name': 'Item A', 'quantity': 2, 'unit_price': 115.50, 'tax_percent': 15.5},
        {'name': 'Item B', 'quantity': 1, 'unit_price': 50.00, 'tax_percent': 5},
        {'name': 'Item C', 'quantity': 3, 'unit_price': 10.00, 'tax_percent': 0},
    ]
    
    total = sum(item['quantity'] * item['unit_price'] for item in items)
    total_tax = sum(calculate_tax(item['quantity'] * item['unit_price'], item['tax_percent']) 
                    for item in items if item['tax_percent'] != 0 and item['tax_percent'] != 'exempt')
    
    print(f"\n📝 Sample Receipt Tax Calculation:")
    print(f"   Subtotal (tax-inclusive): ${total:.2f}")
    print(f"   Total Tax: ${total_tax:.2f}")
    print(f"   Tax Exclusive Subtotal: ${total - total_tax:.2f}")

def test_close_fiscal_day(receipts_submitted: List[Dict]):
    """Test closing the fiscal day"""
    print_section("6. CLOSE FISCAL DAY")
    
    # Get current state before closing
    state = get_current_fiscal_state()
    print(f"📊 Current state before closing:")
    print(f"   Day number: {state['fiscal_day_no']}")
    print(f"   Receipts today: {state['receipt_counter']}")
    print(f"   Day open: {state['is_day_open']}")
    
    if not state['is_day_open']:
        print("⚠️ Fiscal day is already closed!")
        return True
    
    # Generate day counters from submitted receipts
    if receipts_submitted:
        print(f"\n📈 Generating fiscal day counters from {len(receipts_submitted)} receipts...")
        counters = MockDataGenerator.generate_day_counters(receipts_submitted)
        
        print("   Counters generated:")
        for counter in counters:
            print(f"     - {counter['fiscalCounterType']}: ${counter['fiscalCounterValue']:.2f}")
    else:
        print("\n⚠️ No receipts submitted today. Closing empty day...")
        counters = []
    
    # Close the day
    print("\n🔒 Closing fiscal day...")
    result = close_day(fiscal_day_counters=counters)
    
    if 'error' in result:
        print(f"❌ Failed to close day: {result['error']}")
        return False
    else:
        print("✅ Fiscal day closed successfully!")
        print_dict(result)
        
        # Check new state
        new_state = get_current_fiscal_state()
        print(f"\n📊 New state after closing:")
        print(f"   Day number: {new_state['fiscal_day_no']}")
        print(f"   Receipt counter: {new_state['receipt_counter']}")
        print(f"   Day open: {new_state['is_day_open']}")
        
        return True

def test_error_scenarios():
    """Test error handling scenarios"""
    print_section("7. ERROR HANDLING SCENARIOS")
    
    # Test 1: Submit receipt without opening day first
    print("\n📝 Test 1: Submit receipt without opening day")
    state = get_current_fiscal_state()
    was_open = state['is_day_open']
    
    # Close day if open
    if was_open:
        close_day()
    
    # Try to submit receipt
    result = fiscalise_receipt(
        items=[{'name': 'Test', 'quantity': 1, 'unit_price': 10.00, 'tax_percent': 15.5}],
        payment_amount=10.00,
        invoice_no='TEST-ERROR-001',
        payment_method='CASH'
    )
    
    if result.get('error'):
        print(f"   ✅ Expected error received: {result['error'][:50]}...")
    else:
        print(f"   ❌ Should have failed but didn't")
    
    # Reopen day if it was open
    if was_open:
        print("\n   Reopening day...")
        open_day()
    
    # Test 2: Missing required fields
    print("\n📝 Test 2: Missing required fields")
    try:
        result = fiscalise_receipt(
            items=[],  # Empty items list
            payment_amount=10.00,
            invoice_no='TEST-ERROR-002',
            payment_method='CASH'
        )
        if result.get('error'):
            print(f"   ✅ Error handled: {result['error'][:50]}...")
    except Exception as e:
        print(f"   ✅ Exception caught: {str(e)[:50]}...")
    
    print("\n✅ Error handling tests complete!")

def test_full_day_simulation():
    """Simulate a complete business day"""
    print_section("🎯 FULL BUSINESS DAY SIMULATION")
    
    print("This simulation will:")
    print("  1. Open a fiscal day")
    print("  2. Process multiple receipts (random sales)")
    print("  3. Show current state between receipts")
    print("  4. Close the day with proper counters")
    print("  5. Display final summary")
    
    input("\nPress Enter to start simulation...")
    
    # Open day
    print("\n🔓 Opening fiscal day...")
    result = open_day()
    if 'error' in result:
        print(f"❌ Failed to open day: {result['error']}")
        return
    
    day_number = result.get('fiscalDayNo')
    print(f"✅ Day {day_number} opened!")
    
    # Process random number of receipts
    num_receipts = random.randint(3, 8)
    receipts = []
    
    for i in range(num_receipts):
        print(f"\n--- Transaction {i+1} of {num_receipts} ---")
        
        # Generate random sale
        items = MockDataGenerator.generate_random_items(min_items=1, max_items=4)
        total = MockDataGenerator.calculate_total(items)
        
        print(f"   Sale total: ${total:.2f}")
        print(f"   Items: {len(items)}")
        
        # Process payment
        result = fiscalise_receipt(
            items=items,
            payment_amount=total,
            invoice_no=f"SIM-{datetime.now().strftime('%H%M%S')}-{i+1}",
            payment_method=random.choice(['CASH', 'CARD']),
            buyer_name=MockDataGenerator.get_random_buyer()['name'] if random.choice([True, False]) else None
        )
        
        if result.get('success'):
            receipts.append({
                'receipt_num': result['receipt_counter'],
                'amount': total,
                'qr_code': result['qr_code']
            })
            print(f"   ✅ Receipt #{result['receipt_counter']} fiscalised")
        else:
            print(f"   ❌ Failed: {result.get('error')}")
        
        # Show current state
        state = get_current_fiscal_state()
        print(f"   📊 Day {state['fiscal_day_no']}, Receipts: {state['receipt_counter']}")
    
    # Close day
    print(f"\n🔒 Closing day {day_number}...")
    
    # Generate counters from actual receipts
    if receipts:
        counters = MockDataGenerator.generate_day_counters([
            {'items': [{'name': 'Item', 'quantity': 1, 'unit_price': r['amount'], 'tax_percent': 15.5}]}
            for r in receipts
        ])
    else:
        counters = []
    
    close_result = close_day(fiscal_day_counters=counters)
    
    if 'error' not in close_result:
        print("✅ Day closed successfully!")
        
        # Final summary
        print_section("📊 DAY SUMMARY")
        print(f"   Day Number: {day_number}")
        print(f"   Total Receipts: {len(receipts)}")
        print(f"   Total Sales: ${sum(r['amount'] for r in receipts):.2f}")
        print(f"   Average Sale: ${sum(r['amount'] for r in receipts)/len(receipts):.2f}" if receipts else "   No sales")
        
        # Display QR codes (first 3)
        if receipts:
            print(f"\n   Sample QR Codes:")
            for receipt in receipts[:3]:
                print(f"     Receipt #{receipt['receipt_num']}: {receipt['qr_code'][:80]}...")
    else:
        print(f"❌ Failed to close day: {close_result.get('error')}")

def generate_report(receipts: List[Dict]):
    """Generate a summary report of fiscalised receipts"""
    print_section("📊 FISCALISATION REPORT")
    
    if not receipts:
        print("No receipts to report")
        return
    
    total_amount = sum(r['result'].get('receipt_counter', 0) for r in receipts)
    
    print(f"Total Receipts: {len(receipts)}")
    print(f"Total Amount: ${total_amount:.2f}")
    print(f"Last Receipt #: {receipts[-1]['result']['receipt_counter'] if receipts else 0}")
    print(f"Last Global #: {receipts[-1]['result']['receipt_global_no'] if receipts else 0}")
    
    # Save report to file
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_receipts': len(receipts),
        'total_amount': total_amount,
        'receipts': [
            {
                'receipt_id': r['result'].get('receipt_id'),
                'counter': r['result']['receipt_counter'],
                'global_no': r['result']['receipt_global_no'],
                'amount': r['receipt_data']['payment_amount'],
                'invoice': r['receipt_data']['invoice_no'],
                'timestamp': datetime.now().isoformat()
            }
            for r in receipts
        ]
    }
    
    with open('fiscal_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📁 Report saved to: fiscal_report.json")

# ============================================
# MAIN EXECUTION
# ============================================

def main():
    """Main demo execution"""
    print("\n" + "=" * 60)
    print("  ZIMRA FISCAL DEVICE INTEGRATION - DEMO")
    print("=" * 60)
    print("\nThis demo will test all fiscal device functionality")
    print("Make sure you have:")
    print("  1. Set up environment variables (or use defaults)")
    print("  2. Registered the device (first run)")
    print("  3. Internet connection to ZIMRA servers")
    
    input("\nPress Enter to continue or Ctrl+C to cancel...")
    
    try:
        # Step 1: Initial setup
        if not test_initial_setup():
            print("\n❌ Initial setup failed. Please check your configuration.")
            return
        
        # Step 2: Fiscal day operations
        if not test_fiscal_day_operations():
            print("\n❌ Fiscal day operations failed.")
            return
        
        # Step 3: Tax calculations
        test_tax_calculations()
        
        # Step 4: Single receipt
        receipt = test_single_receipt()
        
        # Step 5: Multiple receipts
        receipts = test_multiple_receipts(num_receipts=3)
        
        # Step 6: Error scenarios
        test_error_scenarios()
        
        # Step 7: Full day simulation (optional)
        simulate_full = input("\n🎯 Run full day simulation? (y/n): ").lower().strip()
        if simulate_full == 'y':
            test_full_day_simulation()
        
        # Step 8: Close day
        close_now = input("\n🔒 Close fiscal day now? (y/n): ").lower().strip()
        if close_now == 'y':
            all_receipts = []
            if receipt:
                all_receipts.append({'receipt_data': receipt, 'result': receipt})
            if receipts:
                all_receipts.extend(receipts)
            
            test_close_fiscal_day(all_receipts)
        
        # Generate report
        all_receipts = []
        if receipt:
            all_receipts.append({'receipt_data': receipt, 'result': receipt})
        if receipts:
            all_receipts.extend(receipts)
        
        if all_receipts:
            generate_report(all_receipts)
        
        print_section("✅ DEMO COMPLETED SUCCESSFULLY")
        print("All fiscal device functions tested!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

def quick_test():
    """Quick test with minimal setup"""
    print("\n🚀 Running quick test...")
    
    # Quick ping test
    if ping_device():
        print("✅ Device reachable")
    else:
        print("❌ Device not reachable")
        return
    
    # Quick config check
    config = get_device_config()
    if 'error' not in config:
        print(f"✅ Device configured for: {config.get('taxPayerName')}")
    
    # Quick receipt test
    result = fiscalise_receipt(
        items=[
            {'name': 'Test Product', 'quantity': 1, 'unit_price': 10.00, 'tax_percent': 15.5}
        ],
        payment_amount=10.00,
        invoice_no=f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        payment_method='CASH'
    )
    
    if result.get('success'):
        print(f"✅ Test receipt fiscalised! Receipt #{result['receipt_counter']}")
        print(f"   QR: {result['qr_code']}")
    else:
        print(f"❌ Test failed: {result.get('error')}")

if __name__ == '__main__':
    # Check command line arguments
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--quick':
            quick_test()
        elif sys.argv[1] == '--reset':
            reset_local_state()
            print("Local fiscal state reset!")
        else:
            print("Usage: python demo_fiscal_integration.py [--quick | --reset]")
    else:
        main()