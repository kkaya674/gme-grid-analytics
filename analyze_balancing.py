"""
MSD/MB Balancing Market Analysis

Comprehensive analysis of balancing markets with detailed price and volume visualizations.

Usage:
    python analyze_balancing.py --date 2025-12-30
    python analyze_balancing.py  # Uses yesterday by default
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import date, timedelta

sns.set_style("whitegrid")

ITALIAN_ZONES = ['NORD', 'CNOR', 'CSUD', 'SUD', 'CALA', 'SICI', 'SARD']


def analyze_market(market_name, market_file, mgp_file, output_dir, date_str):
    """Comprehensive balancing market analysis with price and volume charts."""
    
    print(f"\n=== {market_name} BALANCING ANALYSIS ===\n")
    
    # Load data
    market_df = pd.read_csv(market_file)
    market_df.columns = [c.lower() for c in market_df.columns]
    
    mgp = pd.read_csv(mgp_file)
    mgp.columns = [c.lower() for c in mgp.columns]
    
    # MB has different column structure - map to common names
    if market_name == "MB":
        # MB uses volumespurchased/soldnotrevoked
        if 'volumespurchasednotrevoked' in market_df.columns:
            market_df['volumespurchased'] = market_df['volumespurchasednotrevoked'].fillna(0)
            market_df['volumessold'] = market_df['volumessoldnotrevoked'].fillna(0)
    
    # Filter Italian zones
    market_it = market_df[market_df['zone'].isin(ITALIAN_ZONES)].copy()
    
    # Use MAXIMUM prices (more relevant for market analysis)
    # For buying: use minimum purchasing price (what buyers pay at minimum)
    # For selling: use maximum selling price (what sellers get at maximum)
    if 'minimumpurchasingprice' in market_it.columns:
        market_it['buy_price'] = market_it['minimumpurchasingprice'].fillna(0)
    else:
        market_it['buy_price'] = market_it['averagepurchasingprice'].fillna(0)
    
    if 'maximumsellingprice' in market_it.columns:
        market_it['sell_price'] = market_it['maximumsellingprice'].fillna(0)
    else:
        market_it['sell_price'] = market_it['averagesellingprice'].fillna(0)
    
    print(f"Total {market_name} records (Italian zones): {len(market_it)}")
    print(f"Sessions with activity: {len(market_it[(market_it['volumespurchased']>0) | (market_it['volumessold']>0)])}")
    print(f"Non-zero buy prices: {(market_it['buy_price'] > 0).sum()}")
    print(f"Non-zero sell prices: {(market_it['sell_price'] > 0).sum()}")
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # === PLOT 1: Zone-specific price comparison (MSD/MB buy/sell vs MGP) ===
    fig, axes = plt.subplots(4, 2, figsize=(16, 14))
    axes = axes.flatten()
    
    # Calculate global min/max for consistent y-axis across all zones
    all_buy_prices = []
    all_sell_prices = []
    all_mgp_prices = []
    
    for zone in ITALIAN_ZONES:
        zone_market = market_it[market_it['zone'] == zone]
        zone_mgp = mgp[mgp['zone'] == zone]
        
        if len(zone_market) > 0:
            hourly_market = zone_market.groupby('hour').agg({
                'buy_price': 'mean',
                'sell_price': 'mean'
            })
            all_buy_prices.extend(hourly_market['buy_price'].values)
            all_sell_prices.extend(hourly_market['sell_price'].values)
        
        if len(zone_mgp) > 0:
            hourly_mgp = zone_mgp.groupby('hour')['price'].mean()
            all_mgp_prices.extend(hourly_mgp.values)
    
    # Determine global y-axis limits
    all_prices = all_buy_prices + all_sell_prices + all_mgp_prices
    if len(all_prices) > 0:
        y_min = min([p for p in all_prices if p > 0]) * 0.9 if any(p > 0 for p in all_prices) else 0
        y_max = max(all_prices) * 1.1
    else:
        y_min, y_max = 0, 100
    
    # Now plot with consistent scale
    for idx, zone in enumerate(ITALIAN_ZONES):
        ax = axes[idx]
        zone_market = market_it[market_it['zone'] == zone].sort_values('hour')
        zone_mgp = mgp[mgp['zone'] == zone].sort_values('hour')
        
        if len(zone_market) > 0 and len(zone_mgp) > 0:
            # Average by hour (handle multiple periods)
            hourly_market = zone_market.groupby('hour').agg({
                'buy_price': 'mean',
                'sell_price': 'mean'
            })
            hourly_mgp = zone_mgp.groupby('hour')['price'].mean()
            
            hours = hourly_market.index
            
            # Plot 3 lines - keep zeros as zeros (no NaN replacement)
            ax.plot(hours, hourly_market['buy_price'], 
                   marker='o', label=f'{market_name} Buy (Min)', color='#d62728', linewidth=2, markersize=4)
            ax.plot(hours, hourly_market['sell_price'], 
                   marker='s', label=f'{market_name} Sell (Max)', color='#1f77b4', linewidth=2, markersize=4)
            
            # MGP baseline
            if len(hourly_mgp) > 0:
                ax.plot(hourly_mgp.index, hourly_mgp.values, 
                       marker='^', label='MGP', color='#2ca02c', linewidth=2, linestyle='--', markersize=4)
        
        ax.set_xlabel('Hour', fontsize=9)
        ax.set_ylabel('Price (€/MWh)', fontsize=9)
        ax.set_title(f'{zone}', fontweight='bold', fontsize=10)
        ax.legend(fontsize=8, loc='best')
        ax.grid(alpha=0.3)
        ax.set_xticks(range(1, 25, 4))
        
        # Apply consistent y-axis scale
        ax.set_ylim(y_min, y_max)
    
    axes[7].axis('off')
    fig.suptitle(f'{market_name} vs MGP Prices - {date_str}', fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/{market_name.lower()}_zone_price_comparison.png', dpi=200, bbox_inches='tight')
    print(f"  ✓ {market_name.lower()}_zone_price_comparison.png")
    plt.close()
    
    # === PLOT 4: Buy Volumes (Bar chart) ===
    fig, axes = plt.subplots(4, 2, figsize=(16, 14))
    axes = axes.flatten()
    
    for idx, zone in enumerate(ITALIAN_ZONES):
        ax = axes[idx]
        zone_data = market_it[market_it['zone'] == zone].sort_values('hour')
        
        if len(zone_data) > 0:
            hourly_vol = zone_data.groupby('hour')['volumespurchased'].sum()
            hours = hourly_vol.index
            
            ax.bar(hours, hourly_vol.values, color='#d62728', alpha=0.7)
            ax.set_xlabel('Hour', fontsize=9)
            ax.set_ylabel('Volume (MWh)', fontsize=9)
            ax.set_title(f'{zone} - Total: {hourly_vol.sum():.0f} MWh', 
                        fontweight='bold', fontsize=10)
            ax.grid(alpha=0.3, axis='y')
    
    axes[7].axis('off')
    fig.suptitle(f'{market_name} Buy Volumes - {date_str}', fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/{market_name.lower()}_buy_volumes.png', dpi=200, bbox_inches='tight')
    print(f"  ✓ {market_name.lower()}_buy_volumes.png")
    plt.close()
    
    # === PLOT 5: Sell Volumes (Bar chart) ===
    fig, axes = plt.subplots(4, 2, figsize=(16, 14))
    axes = axes.flatten()
    
    for idx, zone in enumerate(ITALIAN_ZONES):
        ax = axes[idx]
        zone_data = market_it[market_it['zone'] == zone].sort_values('hour')
        
        if len(zone_data) > 0:
            hourly_vol = zone_data.groupby('hour')['volumessold'].sum()
            hours = hourly_vol.index
            
            ax.bar(hours, hourly_vol.values, color='#1f77b4', alpha=0.7)
            ax.set_xlabel('Hour', fontsize=9)
            ax.set_ylabel('Volume (MWh)', fontsize=9)
            ax.set_title(f'{zone} - Total: {hourly_vol.sum():.0f} MWh', 
                        fontweight='bold', fontsize=10)
            ax.grid(alpha=0.3, axis='y')
    
    axes[7].axis('off')
    fig.suptitle(f'{market_name} Sell Volumes - {date_str}', fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/{market_name.lower()}_sell_volumes.png', dpi=200, bbox_inches='tight')
    print(f"  ✓ {market_name.lower()}_sell_volumes.png")
    plt.close()
    
    print(f"\n✅ {market_name} analysis complete - 3 visualizations created\n")


def main():
    parser = argparse.ArgumentParser(description='Analyze MSD/MB balancing markets')
    parser.add_argument('--date', type=str, default=None,
                       help='Date to analyze (YYYY-MM-DD), defaults to yesterday')
    
    args = parser.parse_args()
    
    # Default to yesterday if no date provided
    if args.date is None:
        target_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"Using default date: {target_date}")
    else:
        target_date = args.date
    
    # Paths
    base_dir = Path(__file__).parent
    data_dir = base_dir / "data"
    output_dir = base_dir / "analysis"
    
    msd_file = data_dir / f"MSD_ME_MSDExAnteResults_{target_date}.csv"
    mb_file = data_dir / f"MB_ME_MBResults_{target_date}.csv"
    mgp_file = data_dir / f"MGP_ME_ZonalPrices_{target_date}.csv"
    
    # Check MGP file (required for comparison)
    if not mgp_file.exists():
        print(f"Error: MGP file required: {mgp_file}")
        return
    
    # Analyze MSD
    if msd_file.exists():
        analyze_market("MSD", str(msd_file), str(mgp_file), str(output_dir), target_date)
    else:
        print(f"Warning: MSD file not found: {msd_file}")
    
    # Analyze MB
    if mb_file.exists():
        analyze_market("MB", str(mb_file), str(mgp_file), str(output_dir), target_date)
    else:
        print(f"Warning: MB file not found: {mb_file}")
    
    print("✅ All balancing analysis complete!\n")


if __name__ == "__main__":
    main()
