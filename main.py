import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv

# Ensure we can import from src
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from gme_api.client import GMEClient

def main():
    # Load environment variables (GME_USERNAME, GME_PASSWORD)
    load_dotenv()
    
    username = os.getenv("GME_USERNAME")
    password = os.getenv("GME_PASSWORD")
    
    if not username or not password:
        print("Error: GME_USERNAME and GME_PASSWORD must be set in .env file.")
        return

    # Use yesterday's date for demonstration
    target_date = date.today() - timedelta(days=1)
    
    print(f"--- GME Data Fetching Demo ({target_date}) ---")
    
    with GMEClient(username, password) as client:
        # 1. Fetch and Save MGP Zonal Prices
        print(f"Fetching MGP Zonal Prices...")
        success = client.fetch_and_save_csv("ME_ZonalPrices", "MGP", target_date, target_date)
        if success:
            print(f"  [SUCCESS] MGP Zonal Prices saved to data/")
        else:
            print(f"  [FAILED] Could not fetch MGP data.")

        # 2. Fetch and Save MGP Transmission Limits
        print(f"Fetching MGP Transmission Limits...")
        success = client.fetch_and_save_csv("ME_TransmissionLimits", "MGP", target_date, target_date)
        if success:
            print(f"  [SUCCESS] MGP Transmission Limits saved to data/")

        # 3. Fetch and Save MB Zonal Prices
        print(f"Fetching MB Zonal Prices...")
        success = client.fetch_and_save_csv("ME_ZonalPrices", "MB", target_date, target_date)
        if success:
            print(f"  [SUCCESS] MB Zonal Prices saved to data/")

        # 4. Fetch and Save MSD Zonal Prices
        print(f"Fetching MSD Zonal Prices...")
        success = client.fetch_and_save_csv("ME_ZonalPrices", "MSD", target_date, target_date)
        if success:
            print(f"  [SUCCESS] MSD Zonal Prices saved to data/")

        # 5. Check Quotas
        quotas = client.get_my_quotas()
        if quotas:
            print(f"\nRemaining Quotas: {quotas}")

if __name__ == "__main__":
    main()
