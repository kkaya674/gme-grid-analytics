import os
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
print(f"Fetching MGP data for {test_date}...\n")

result = client.get_electricity_prices("MGP", test_date)

print("=" * 80)
print("RAW API RESPONSE:")
print("=" * 80)
print(f"Type: {type(result)}")
print(f"\nKeys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
print("\n" + "=" * 80)
print("FULL RESPONSE (formatted):")
print("=" * 80)
print(json.dumps(result, indent=2, default=str))

if isinstance(result, dict):
    print("\n" + "=" * 80)
    print("ANALYZING STRUCTURE:")
    print("=" * 80)
    
    for key, value in result.items():
        print(f"\n{key}:")
        print(f"  Type: {type(value)}")
        if isinstance(value, list):
            print(f"  Length: {len(value)}")
            if len(value) > 0:
                print(f"  First item: {value[0]}")
                print(f"  First item keys: {list(value[0].keys()) if isinstance(value[0], dict) else 'N/A'}")
        elif isinstance(value, dict):
            print(f"  Keys: {list(value.keys())}")
            for subkey, subvalue in list(value.items())[:3]:
                print(f"    {subkey}: {type(subvalue)} = {subvalue if not isinstance(subvalue, (list, dict)) else f'{type(subvalue).__name__} with {len(subvalue)} items'}")
