import pandas as pd
from typing import List, Dict, Any, Optional
import io
import json

def flatten_gme_response(data: Any) -> pd.DataFrame:
    """
    Flattens the typical GME JSON response into a pandas DataFrame.
    GME responses are often lists of dictionaries.
    """
    if not data:
        return pd.DataFrame()
    
    if isinstance(data, dict):
        # Sometimes it's wrapped in a single key or is a single record
        # Let's try to find a list inside
        for key, value in data.items():
            if isinstance(value, list):
                data = value
                break
        else:
            data = [data]
            
    df = pd.DataFrame(data)
    
    # Common column cleanups for GME data
    # GME dates are often YYYYMMDD in JSON, but sometimes strings
    # We might want to keep them as strings or convert to datetime if needed
    
    return df

def process_market_data(df: pd.DataFrame, market_type: str) -> pd.DataFrame:
    """
    Apply market-specific processing.
    Handles regions, hours, and granularity.
    """
    if df.empty:
        return df
    
    # Normalize column names to lowercase for consistency
    df.columns = [c.lower() for c in df.columns]
    
    # Generic Italian Market regions mapping if needed
    # (NORD, CNOR, CSUD, SUD, SICI, SARD, etc.)
    
    # Handle time/hour formatting if exists
    if 'hour' in df.columns:
        # Some markets have 1-24, others 0-23
        pass
        
    return df

def save_to_csv(df: pd.DataFrame, file_path: str) -> bool:
    """
    Saves the DataFrame to a CSV file.
    """
    try:
        df.to_csv(file_path, index=False)
        return True
    except Exception as e:
        print(f"Failed to save CSV to {file_path}: {e}")
        return False
