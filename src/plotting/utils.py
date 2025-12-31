"""
GME Plotting Utilities
"""

import os
from datetime import date, timedelta


def get_latest_data_file(data_dir, market, endpoint):
    """
    Find the latest data file for a market.
    
    Args:
        data_dir: Data directory path
        market: Market name (MGP, MB, MSD)
        endpoint: Endpoint name (ME_ZonalPrices, etc.)
        
    Returns:
        Path to latest data file or None
    """
    import glob
    pattern = os.path.join(data_dir, f"{market}_{endpoint}_*.csv")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files)  # Latest by filename


def format_market_name(market):
    """Format market name for display."""
    names = {
        'MGP': 'Day-Ahead Market (MGP)',
        'MB': 'Balancing Market (MB)',
        'MSD': 'Dispatch Services Market (MSD)'
    }
    return names.get(market, market)
