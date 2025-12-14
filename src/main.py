import os
import sys
from datetime import date
from dotenv import load_dotenv

# Add src to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from gme_api.client import GMEClient

# Load .env file from project root
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path, override=True)
    print(f"Loaded configuration from {dotenv_path}")
else:
    print(f"WARNING: .env file not found at {dotenv_path}")

def main():
    print("Starting GME Tool...")
    
    username = os.getenv("GME_USERNAME")
    password = os.getenv("GME_PASSWORD")

    if not username or not password:
        print("ERROR: Username or password not found in .env file!")
        sys.exit(1)

    print(f"User: {username}")
    
    # Example usage
    with GMEClient(username, password) as client:
        today = date.today()
        print(f"Fetching data for {today}...")
        
        # Example: Fetch MGP prices
        prices = client.get_electricity_prices("MGP", today)
        if prices:
            print("Prices fetched successfully.")
            import json
            print(json.dumps(prices, indent=2))
        else:
            print("Failed to fetch prices.")

if __name__ == "__main__":
    main()

