import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import date, datetime
from gme_api.client import GMEClient
import json

def test_market(client, market_type, market, test_date):
    """Test a specific market and display results."""
    print(f"\n{'='*80}")
    print(f"Testing {market_type.upper()} - {market}")
    print(f"Date: {test_date}")
    print(f"{'='*80}")
    
    try:
        if market_type == 'electricity':
            if market == 'MB':
                result = client.get_mb_results(test_date)
            else:
                result = client.get_electricity_prices(market, test_date)
        elif market_type == 'gas':
            result = client.get_gas_prices(market, test_date)
        elif market_type == 'environmental':
            result = client.get_environmental_data(market, test_date)
        else:
            print(f"Unknown market type: {market_type}")
            return False
        
        if result:
            print(f"✓ Success! Received data")
            print(f"  Type: {type(result)}")
            
            if isinstance(result, list):
                print(f"  Records: {len(result)}")
                if len(result) > 0:
                    print(f"  First record: {json.dumps(result[0], indent=2, default=str)}")
            elif isinstance(result, dict):
                print(f"  Keys: {list(result.keys())}")
                for key, value in result.items():
                    if isinstance(value, list):
                        print(f"  {key}: {len(value)} items")
                        if len(value) > 0:
                            print(f"    First item: {json.dumps(value[0], indent=4, default=str)}")
                    else:
                        print(f"  {key}: {value}")
            
            return True
        else:
            print("✗ Failed - No data returned")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("GME API Test Suite")
    print("=" * 80)
    
    username = os.getenv("GME_USERNAME")
    password = os.getenv("GME_PASSWORD")
    
    if not username or not password:
        print("ERROR: GME_USERNAME and GME_PASSWORD environment variables must be set")
        print("Please set them in your .env file")
        return
    
    print(f"Username: {username}")
    print("Attempting authentication...")
    
    client = GMEClient(username, password)
    
    if not client.login():
        print("✗ Authentication failed!")
        return
    
    print("✓ Authentication successful!")
    
    test_date = date(2024, 11, 1)
    
    tests = [
        ('electricity', 'MGP', 'Day-Ahead Market'),
        ('electricity', 'MI1', 'Intraday Session 1'),
        ('electricity', 'MI2', 'Intraday Session 2'),
        ('electricity', 'MI3', 'Intraday Session 3'),
        ('electricity', 'MSD', 'Ancillary Services Market'),
        ('electricity', 'MB', 'Balancing Market'),
        ('gas', 'MGP-GAS', 'Day-Ahead Gas Market'),
        ('gas', 'MI-GAS', 'Intraday Gas Market'),
        ('environmental', 'TEE', 'Energy Efficiency Certificates'),
    ]
    
    results = []
    
    for market_type, market, description in tests:
        print(f"\n{description}")
        success = test_market(client, market_type, market, test_date)
        results.append((market, success))
    
    print(f"\n\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for market, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8} - {market}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({100*passed//total}%)")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    elif passed > 0:
        print(f"\n⚠️  Some tests failed. Check the logs above.")
    else:
        print(f"\n❌ All tests failed. Please check your credentials and network connection.")

if __name__ == "__main__":
    main()
