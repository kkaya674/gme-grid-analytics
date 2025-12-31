import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv

# Ensure we can import from src


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
    if len(sys.argv) > 1 and sys.argv[1] == "--date":
        # User provided --date argument
        if len(sys.argv) > 2:
            try:
                from datetime import datetime
                datetime.strptime(sys.argv[2], '%Y-%m-%d')
                target_date = sys.argv[2]
            except ValueError:
                print(f"Error: Invalid date format '{sys.argv[2]}'. Use YYYY-MM-DD")
                return
        else:
            print("Error: --date requires a value (YYYY-MM-DD)")
            return
    else:
        # Default to yesterday
        target_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    
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
        else:
            print(f"  [FAILED] Could not fetch MGP Transmission Limits.")

        # 3. Fetch and Save MB Results
        print(f"Fetching MB Results...")
        success = client.fetch_and_save_csv("ME_MBResults", "MB", target_date, target_date)
        if success:
            print(f"  [SUCCESS] MB Results saved to data/")
        else:
            print(f"  [FAILED] Could not fetch MB Results.")

        # 4. Fetch and Save MSD Results
        print(f"Fetching MSD Results...")
        success = client.fetch_and_save_csv("ME_MSDExAnteResults", "MSD", target_date, target_date)
        if success:
            print(f"  [SUCCESS] MSD Results saved to data/")
        else:
            print(f"  [FAILED] Could not fetch MSD Results.")

        # 5. Fetch and Save MGP Transit Flows
        print(f"Fetching MGP Transit Flows...")
        success = client.fetch_and_save_csv("ME_Transits", "MGP", target_date, target_date)
        if success:
            print(f"  [SUCCESS] MGP Transit Flows saved to data/")
        else:
            print(f"  [FAILED] Could not fetch MGP Transit Flows.")

        # 6. Check Quotas
        quotas = client.get_my_quotas()
        if quotas:
            print(f"\nRemaining Quotas: {quotas}")

if __name__ == "__main__":
    main()
