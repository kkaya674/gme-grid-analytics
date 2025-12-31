#!/usr/bin/env python3
"""
Example usage of GME API client.
"""

import os
from datetime import date, timedelta
from dotenv import load_dotenv
from src.gme_api.client import GMEClient

def main():
    # Load environment variables
    load_dotenv()
    
    username = os.getenv("GME_USERNAME")
    password = os.getenv("GME_PASSWORD")
    
    if not username or not password:
        print("Please set GME_USERNAME and GME_PASSWORD in .env file")
        print("Copy .env.example to .env and fill in your credentials")
        return
    
    # Create client
    client = GMEClient(username, password)
    
    # Login
    if not client.login():
        print("Authentication failed. Check your credentials.")
        return
    
    print("Authentication successful!")
    
    # Get yesterday's date
    yesterday = date.today() - timedelta(days=1)
    
    # Example 1: Fetch MGP electricity prices
    print(f"\n1. Fetching MGP electricity prices for {yesterday}")
    mgp_data = client.get_electricity_prices("MGP", yesterday)
    if mgp_data:
        print(f"   Success! Retrieved {len(mgp_data) if isinstance(mgp_data, list) else 'data'}")
    else:
        print("   No data returned")
    
    # Example 2: Fetch MI1 intraday prices
    print(f"\n2. Fetching MI1 intraday prices for {yesterday}")
    mi1_data = client.get_electricity_prices("MI1", yesterday)
    if mi1_data:
        print(f"   Success! Retrieved {len(mi1_data) if isinstance(mi1_data, list) else 'data'}")
    else:
        print("   No data returned")
    
    # Example 3: Fetch gas prices
    print(f"\n3. Fetching MGP-GAS prices for {yesterday}")
    gas_data = client.get_gas_prices("MGP-GAS", yesterday)
    if gas_data:
        print(f"   Success! Retrieved {len(gas_data) if isinstance(gas_data, list) else 'data'}")
    else:
        print("   No data returned")
    
    # Example 4: Fetch environmental data
    print(f"\n4. Fetching TEE environmental data for {yesterday}")
    env_data = client.get_environmental_data("TEE", yesterday)
    if env_data:
        print(f"   Success! Retrieved {len(env_data) if isinstance(env_data, list) else 'data'}")
    else:
        print("   No data returned")
    
    print("\nDone!")

if __name__ == "__main__":
    main()