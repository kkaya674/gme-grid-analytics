import requests
import base64
import zipfile
import io
import json
import os
from datetime import date
from typing import Optional, Dict, Any, List, Union
from .utils import flatten_gme_response, process_market_data, save_to_csv

class GMEClient:
    """
    Enhanced Python Client for GME (Gestore Mercati Energetici) API Service.
    Supports data fetching, decoding, processing, and CSV storage.
    """
    def __init__(self, username: str, password: str, base_url: str = "https://api.mercatoelettrico.org/request"):
        self.username = username
        self.password = password
        self.base_url = base_url
        self.token: Optional[str] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def login(self) -> bool:
        """Authenticates with the GME API and retrieves a JWT token."""
        url = f"{self.base_url}/api/v1/Auth"
        payload = {
            "login": self.username,
            "password": self.password
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            # Check both success and Success
            is_success = result.get("success") or result.get("Success")
            if is_success:
                self.token = result.get("token")
                return True
            else:
                reason = result.get("reason") or result.get("Reason")
                print(f"Authentication failed: {reason}")
                return False
        except Exception as e:
            print(f"Login request failed: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Handles API requests with automatic re-authentication."""
        if not self.token and not self.login():
            raise Exception("Authentication required")

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
                    response = requests.request(method, url, headers=headers, params=params, json=data)
                else:
                    raise Exception("Session expired and re-authentication failed")

            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Request to {endpoint} failed: {e}")
            return None

    def decode_response(self, response_json: Dict[str, Any]) -> Any:
        """Decodes Base64 encoded zip content and returns JSON data."""
        content_b64 = response_json.get("ContentResponse") or response_json.get("contentResponse")
        if not content_b64:
            return response_json

        try:
            zip_data = base64.b64decode(content_b64)
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                # GME usually returns one file in the zip
                for filename in z.namelist():
                    with z.open(filename) as f:
                        content = f.read()
                        try:
                            return json.loads(content)
                        except json.JSONDecodeError:
                            return content # Return raw if not JSON
        except Exception as e:
            print(f"Decoding failed: {e}")
            return None

    def fetch_data(self, data_name: str, segment: str, start_date: Union[date, str, int], end_date: Union[date, str, int], platform: str = "PublicMarketResults", attributes: Dict = None) -> Any:
        """Base method for fetching data from RequestData endpoint."""
        
        # Convert dates to yyyyMMdd format
        def fmt_date(d):
            if isinstance(d, date): return int(d.strftime("%Y%m%d"))
            if isinstance(d, str): return int(d.replace("-", "").replace("/", ""))
            return int(d)

        payload = {
            "Platform": platform,
            "Segment": segment,
            "DataName": data_name,
            "IntervalStart": fmt_date(start_date),
            "IntervalEnd": fmt_date(end_date),
            "Attributes": attributes or {}
        }

        response = self.make_request("/api/v1/RequestData", method="POST", data=payload)
        if response:
            return self.decode_response(response)
        return None

    def fetch_and_save_csv(self, data_name: str, segment: str, start_date: Union[date, str, int], end_date: Union[date, str, int], output_dir: str = "workspace") -> bool:
        """Fetches data, processes it, and saves as CSV."""
        data = self.fetch_data(data_name, segment, start_date, end_date)
        if not data:
            return False
        
        df = flatten_gme_response(data)
        if df.empty:
            return False
        
        df = process_market_data(df, segment)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        file_name = f"{segment}_{data_name}_{start_date}.csv".replace("/", "_")
        file_path = os.path.join(output_dir, file_name)
        
        return save_to_csv(df, file_path)

    # Simplified interface methods for common markets
    def get_mgp_prices(self, date_obj: date):
        return self.fetch_data("ME_ZonalPrices", "MGP", date_obj, date_obj)

    def get_msd_exante(self, date_obj: date):
        return self.fetch_data("ME_MSDExAnteResults", "MSD", date_obj, date_obj)

    def get_mb_results(self, date_obj: date):
        return self.fetch_data("ME_MBResults", "MB", date_obj, date_obj)

    # Generic method for any ME_ data
    def get_market_data(self, market: str, category: str, date_obj: date):
        """
        Example: get_market_data("MGP", "ZonalPrices", date(2023,1,1))
        """
        data_name = f"ME_{category}"
        return self.fetch_data(data_name, market, date_obj, date_obj)

    def get_my_quotas(self) -> Dict[str, Any]:
        """Checks remaining service limits."""
        return self.make_request("/api/v1/GetMyQuotas")
