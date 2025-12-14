import requests
from typing import Optional, Dict, Any, List, Union
from datetime import date
import base64
import zipfile
import io
import json

class GMEClient:
    def __init__(self, username: str, password: str):
        self.base_url = "https://api.mercatoelettrico.org/request/api/v1"
        self.username = username
        self.password = password
        self.token = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def login(self) -> bool:
        endpoint = "/Auth"
        url = f"{self.base_url}{endpoint}"
        payload = {
            "login": self.username,
            "password": self.password
        }
        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            if result.get("success"):
                self.token = result.get("token")
                return True
            return False

        except Exception:
            return False

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self.token:
            if not self.login():
                raise Exception("Authentication failed")

        # The base URL for RequestData is .../request/api/v1/RequestData
        # But the endpoint passed here is usually just the suffix.
        # However, for the new structure, we are always hitting /RequestData with a POST body.
        
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code == 401:
                if self.login():
                    headers = self._get_headers()
                    if method == "GET":
                        response = requests.get(url, headers=headers, params=params)
                    elif method == "POST":
                        response = requests.post(url, headers=headers, json=data)
                else:
                    raise Exception("Re-authentication failed")

            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(f"Request failed: {e}")
            # Print response text for debugging if available
            if 'response' in locals():
                print(f"Response: {response.text}")
            return None

    def decode_response(self, response_data: Dict[str, Any]) -> Any:
        """
        Decodes the 'contentResponse' from the API response.
        It expects a Base64 encoded ZIP file containing a JSON file.
        """
        if not response_data or "contentResponse" not in response_data:
            return response_data

        content_b64 = response_data["contentResponse"]
        if not content_b64:
            return None

        try:
            # Decode Base64
            zip_data = base64.b64decode(content_b64)
            
            # Open ZIP
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                # Assume there is only one file or we want the first one
                file_list = z.namelist()
                if not file_list:
                    return None
                
                # Look for a json file
                json_file = next((f for f in file_list if f.endswith('.json')), None)
                
                if json_file:
                    with z.open(json_file) as f:
                        return json.load(f)
                else:
                    return None
        except Exception as e:
            print(f"Error decoding response: {e}")
            return None

    def _get_data(self, segment: str, data_name: str, date_obj: date) -> Optional[Dict[str, Any]]:
        """
        Helper to call the RequestData endpoint with the correct structure.
        """
        endpoint = "/RequestData"
        date_str = date_obj.strftime("%Y%m%d")
        
        payload = {
            "Platform": "PublicMarketResults",
            "Segment": segment,
            "DataName": data_name,
            "IntervalStart": date_str,
            "IntervalEnd": date_str
        }
        
        response = self.make_request(endpoint, method="POST", data=payload)
        if response:
            return self.decode_response(response)
        return None

    # Electricity Market (MPE)
    def get_electricity_prices(self, market: str, date_obj: date) -> Optional[Dict[str, Any]]:
        """
        Fetch electricity prices (e.g., PUN) for a specific market and date.
        Markets: MGP (Day-Ahead), MI (Intra-Day), MPEG
        DataName: ME_ZonalPrices
        """
        return self._get_data(market, "ME_ZonalPrices", date_obj)

    def get_electricity_volumes(self, market: str, date_obj: date) -> Optional[Dict[str, Any]]:
        """
        Fetch electricity volumes for a specific market and date.
        DataName: ME_ZonalVolumes
        """
        return self._get_data(market, "ME_ZonalVolumes", date_obj)

    # Gas Market (MGAS)
    def get_gas_prices(self, market: str, date_obj: date) -> Optional[Dict[str, Any]]:
        """
        Fetch gas prices for a specific market and date.
        Markets: MGP-GAS, MI-GAS, MGS (Storage)
        DataName: GAS_ContinuousTrading (for continuous markets)
        """
        # Note: The manual mentions GAS_ContinuousTrading for MGP-GAS, MI-GAS
        return self._get_data(market, "GAS_ContinuousTrading", date_obj)

    def get_gas_volumes(self, market: str, date_obj: date) -> Optional[Dict[str, Any]]:
        """
        Fetch gas volumes for a specific market and date.
        """
        # Gas continuous trading returns both prices and volumes
        return self.get_gas_prices(market, date_obj)

    # Environmental Markets (M-TE / M-GO)
    def get_environmental_data(self, market: str, date_obj: date) -> Optional[Dict[str, Any]]:
        """
        Fetch data for environmental markets.
        Markets: TEE (Energy Efficiency Certificates), GO (Guarantees of Origin)
        DataName: ENV_Results (Generic results) or ENV_AuctionResults
        """
        return self._get_data(market, "ENV_Results", date_obj)


