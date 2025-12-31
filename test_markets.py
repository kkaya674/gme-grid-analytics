import sys
from datetime import date
import json

sys.path.insert(0, '/Users/kkaya674/Desktop/gme_api/src')

from gme_api.client import GMEClient

username = "kubilaykaya1216"
password = "Kubi306504.."

client = GMEClient(username, password)

print("Logging in...")
if not client.login():
    print("Login failed!")
    sys.exit(1)

print("Login successful!\n")

test_date = date(2024, 12, 13)

markets_to_test = [
    ("MGP", "Day-Ahead Market"),
    ("MI1", "First Intraday Session"),
    ("MI2", "Second Intraday Session"),
    ("MSD", "Ancillary Services Market"),
    ("MB", "Balancing Market")
]

for market_code, market_name in markets_to_test:
    print("=" * 80)
    print(f"Testing {market_code} - {market_name}")
    print("=" * 80)
    
    try:
        result = client.get_electricity_prices(market_code, test_date)
        
        if result:
            print(f"✅ Success! Total items: {len(result)}")
            
            if isinstance(result, list) and len(result) > 0:
                first_item = result[0]
                print(f"First item keys: {list(first_item.keys())}")
                print(f"First item: {first_item}")
                
                zones = {}
                for item in result:
                    zone = item.get('Zone', item.get('Zona', 'Unknown'))
                    zones[zone] = zones.get(zone, 0) + 1
                
                print(f"\nZones found: {list(zones.keys())}")
                print(f"PUN count: {zones.get('PUN', 0)}")
        else:
            print(f"❌ No data returned")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n")
