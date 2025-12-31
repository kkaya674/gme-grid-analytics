import requests
import base64
import json
import zipfile
import io
from typing import Optional, Dict, Any

class GMEApiClient:
    """
    Python Client for GME (Gestore Mercati Energetici) API Service.
    Based on the technical guide for 'Servizio API del GME'.
    """

    def __init__(self, base_url: str = "https://api.mercatoelettrico.org/request"):
        self.base_url = base_url
        self.token: Optional[str] = None

    def authenticate(self, login: str, password: str) -> bool:
        """
        2. Authentication
        Endpoint: /api/v1/Auth
        Obtains a JWT token required for subsequent requests.
        """
        url = f"{self.base_url}/api/v1/Auth"
        payload = {
            "Login": login,
            "Password": password
        }
        
        response = requests.post(url, json=payload)
        data = response.json()
        
        if data.get("Success"):
            self.token = data.get("token")
            return True
        else:
            print(f"Authentication Failed: {data.get('Reason')}")
            return False

    def get_quotas(self) -> Dict[str, Any]:
        """
        4. Request User Quotas
        Endpoint: /api/v1/GetMyQuotas
        Checks remaining service limits and consumption.
        """
        if not self.token:
            raise Exception("Authentication required. Call authenticate() first.")

        url = f"{self.base_url}/api/v1/GetMyQuotas"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.get(url, headers=headers)
        return response.json()

    def _fetch_data(self, data_name: str, segment: str, interval_start: int, interval_end: int, platform: str = "PublicMarketResults", attributes: Dict = None) -> Any:
        """
        3. Core Data Request Logic
        Endpoint: /api/v1/RequestData
        Handles POST request and Base64/Zip decoding.
        """
        if not self.token:
            raise Exception("Authentication required.")

        url = f"{self.base_url}/api/v1/RequestData"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        payload = {
            "Platform": platform,
            "Segment": segment,
            "DataName": data_name,
            "IntervalStart": interval_start, # Format: yyyyMMdd
            "IntervalEnd": interval_end,     # Format: yyyyMMdd
            "Attributes": attributes or {}
        }

        response = requests.post(url, json=payload, headers=headers)
        res_json = response.json()

        if res_json.get("ContentResponse"):
            return self._decode_response(res_json["ContentResponse"])
        else:
            print(f"Error fetching {data_name}: {res_json.get('ResultRequest')}")
            return None

    def _decode_response(self, base64_string: str) -> Any:
        """Decodes Base64 encoded zip content and returns JSON data."""
        zip_data = base64.b64decode(base64_string)
        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            for filename in z.namelist():
                with z.open(filename) as f:
                    # Logic: Most responses are .json, some might be .xml
                    content = f.read()
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return content # Return raw bytes if not JSON (e.g., XML)

    # =========================================================================
    # ME_ (ELECTRICITY MARKET) INTERFACE METHODS
    # =========================================================================

    def get_me_additional_demand(self, start: int, end: int):
        return self._fetch_data("ME_AdditionalDemand", "MGP", start, end)

    def get_me_cip6(self, start: int, end: int):
        return self._fetch_data("ME_Cip6", "MGP", start, end)

    def get_me_conventional_prices(self, segment: str, start: int, end: int):
        # Segments: MGP, MI1, MI2, MI3, MI4, MI5, MI6, MI7, MA
        return self._fetch_data("ME_ConventionalPrices", segment, start, end)

    def get_me_demand(self, start: int, end: int):
        return self._fetch_data("ME_Demand", "MGP", start, end)

    def get_me_demand_and_supply(self, segment: str, start: int, end: int):
        # Segments: MGP, MI-A1, MI-A2, MI-A3, MI1, MI2, MI3, MI4, MI5, MI6, MI7
        return self._fetch_data("ME_DemandAndSupply", segment, start, end)

    def get_me_european_exchanges(self, start: int, end: int):
        return self._fetch_data("ME_EuropeanExchanges", "MGP", start, end)

    def get_me_forecast_demand(self, start: int, end: int):
        return self._fetch_data("ME_ForecastDemand", "MGP", start, end)

    def get_me_generalised_constraints(self, segment: str, start: int, end: int):
        # Segments: MGP, MI-A1, MI-A2, MI-A3
        return self._fetch_data("ME_GeneralisedConstraints", segment, start, end)

    def get_me_hourly_price(self, start: int, end: int):
        return self._fetch_data("ME_HourlyPrice", "XBID", start, end)

    def get_me_liquidity(self, start: int, end: int):
        return self._fetch_data("ME_Liquidity", "MGP", start, end)

    def get_me_market_coupling(self, start: int, end: int):
        return self._fetch_data("ME_MarketCoupling", "MGP", start, end)

    def get_me_mb_results(self, start: int, end: int):
        return self._fetch_data("ME_MBResults", "MB", start, end)

    def get_me_mlf_results(self, segment: str, start: int, end: int):
        # Segments: MGP, MLT
        return self._fetch_data("ME_MLFResults", segment, start, end)

    def get_me_mpeg_results(self, start: int, end: int):
        return self._fetch_data("ME_MPEGResults", "MPEG", start, end)

    def get_me_msd_ex_ante_results(self, start: int, end: int):
        return self._fetch_data("ME_MSDExAnteResults", "MSD", start, end)

    def get_me_msd_ex_post_results(self, start: int, end: int):
        return self._fetch_data("ME_MSDExPostResults", "MSD", start, end)

    def get_me_mte_results(self, start: int, end: int):
        return self._fetch_data("ME_MTEResults", "MTE", start, end)

    def get_me_pab_results(self, start: int, end: int):
        return self._fetch_data("ME_PABResults", "PAB", start, end)

    def get_me_pce_results(self, start: int, end: int):
        return self._fetch_data("ME_PCEResults", "PCE", start, end)

    def get_me_ppa_notices(self, start: int, end: int):
        return self._fetch_data("ME_PPANotices", "PPA", start, end)

    def get_me_ramp_constraints(self, segment: str, start: int, end: int):
        # Segments: MGP, MI-A1, MI-A2, MI-A3
        return self._fetch_data("ME_RampConstraints", segment, start, end)

    def get_me_transits(self, segment: str, start: int, end: int):
        # Segments: MGP, MI-A1, MI-A2, MI-A3
        return self._fetch_data("ME_Transits", segment, start, end)

    def get_me_transmission_limits(self, segment: str, start: int, end: int):
        # Segments: MA1, MGP, MI-A1, MI-A2, MI-A3, MI1 to MI7, MA
        return self._fetch_data("ME_TransmissionLimits", segment, start, end)

    def get_me_xbid_nomination_platform(self, start: int, end: int):
        return self._fetch_data("ME_XBIDNominationPlatform", "XBID", start, end)

    def get_me_xbid_results(self, start: int, end: int):
        return self._fetch_data("ME_XBIDResults", "XBID", start, end)

    def get_me_zonal_prices(self, segment: str, start: int, end: int, granularity: str = None):
        """
        Attributes: 'GranularityType' can be 'PT15', 'PT30', or 'PT60' (valid for MGP from Oct 2025)
        """
        attr = {"GranularityType": granularity} if granularity else {}
        return self._fetch_data("ME_ZonalPrices", segment, start, end, attributes=attr)

    def get_me_zonal_volumes(self, segment: str, start: int, end: int):
        return self._fetch_data("ME_ZonalVolumes", segment, start, end)

    def get_offers_public_domain(self, segment: str, start: int, end: int):
        """
        5.52 Offers_PublicDomain
        Note: This returns .xml.zip format.
        """
        return self._fetch_data("Offers_PublicDomain", segment, start, end)

# ==========================================
# USAGE SCENARIOS
# ==========================================

if __name__ == "__main__":
    client = GMEApiClient()

    # Scenario 1: Authentication
    # Note: Replace with actual credentials provided by GME
    if client.authenticate("USERNAME", "PASSWORD"):
        print("Logged in successfully.")

        # Scenario 2: Check Quotas
        quotas = client.get_quotas()
        print(f"Quotas: {quotas}")

        # Scenario 3: Get Zonal Prices for Day-Ahead Market (MGP)
        # Dates are in yyyyMMdd format
        prices = client.get_me_zonal_prices(segment="MGP", start=20240101, end=20240102)
        print(f"Zonal Prices: {prices}")

        # Scenario 4: Get XBID Hourly Prices
        xbid_data = client.get_me_hourly_price(start=20240101, end=20240101)
        print(f"XBID Data: {xbid_data}")

        # Scenario 5: Transmission Limits
        limits = client.get_me_transmission_limits(segment="MGP", start=20240101, end=20240101)
        print(f"Limits: {limits}")