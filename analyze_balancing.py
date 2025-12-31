"""
MSD/MB Balancing Market Analysis

Analyze balancing market data (MSD ex-ante and MB results) to identify:
- Balancing volumes and patterns
- Price premiums over MGP
- Zone-specific imbalances
- Time-of-day balancing needs

Usage:
    python analyze_balancing.py --date 2025-12-30
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

sns.set_style("whitegrid")


def analyze_msd(msd_file, mgp_file, output_dir, date_str):
    """Analyze MSD ex-ante balancing data."""
    
    print("\n=== MSD BALANCING ANALYSIS ===\n")
    
    # Load data
    msd = pd.read_csv(msd_file)
    msd.columns = [c.lower() for c in msd.columns]
    
    mgp = pd.read_csv(mgp_file)
    mgp.columns = [c.lower() for c in mgp.columns]
    
    # Filter non-zero volumes
    msd_active = msd[(msd['volumespurchased'] > 0) | (msd['volumessold'] > 0)].copy()
    
    print(f"Total MSD records: {len(msd)}")
    print(f"Active balancing sessions: {len(msd_active)} ({len(msd_active)/len(msd)*100:.1f}%)")
    
    # 1. Volume statistics by zone
    print("\n1. BALANCING VOLUMES BY ZONE")
    zone_stats = msd.groupby('zone').agg({
        'volumespurchased': 'sum',
        'volumessold': 'sum'
    })
    zone_stats['net_purchased'] = zone_stats['volumespurchased'] - zone_stats['volumessold']
    zone_stats['total_volume'] = zone_stats['volumespurchased'] + zone_stats['volumessold']
    zone_stats = zone_stats.sort_values('total_volume', ascending=False)
    
    print("\nTop zones by total balancing volume:")
    print(zone_stats.head(10).to_string())
    
    # 2. Time pattern
    print("\n2. HOURLY BALANCING PATTERN")
    hourly = msd.groupby('hour').agg({
        'volumespurchased': 'sum',
        'volumessold': 'sum'
    })
    hourly['net'] = hourly['volumespurchased'] - hourly['volumessold']
    
    peak_hour = hourly['volumespurchased'].idxmax()
    print(f"\nPeak upward regulation: Hour {peak_hour} ({hourly.loc[peak_hour, 'volumespurchased']:.0f} MW)")
    
    # 3. Price premium analysis (MSD vs MGP)
    if 'averagepurchasingprice' in msd.columns and len(msd_active) > 0:
        print("\n3. PRICE PREMIUM ANALYSIS")
        
        # Merge with MGP prices
        msd_with_mgp = msd_active.merge(
            mgp[['hour', 'period', 'zone', 'price']],
            on=['hour', 'period', 'zone'],
            how='left',
            suffixes=('_msd', '_mgp')
        )
        
        # Calculate premium
        msd_with_mgp['premium'] = msd_with_mgp['averagepurchasingprice'] - msd_with_mgp['price']
        
        valid_premium = msd_with_mgp[msd_with_mgp['premium'].notna()]
        if len(valid_premium) > 0:
            print(f"Average balancing premium: €{valid_premium['premium'].mean():.2f}/MWh")
            print(f"Max premium: €{valid_premium['premium'].max():.2f}/MWh")
    
    # Visualizations
    Path(output_dir).mkdir(exist_ok=True)
    
    # Plot 1: Zone imbalance bar chart
    if len(zone_stats) > 0:
        fig, ax = plt.subplots(figsize=(12, 6))
        zones = zone_stats.head(10).index
        x = np.arange(len(zones))
        
        ax.bar(x, zone_stats.loc[zones, 'volumespurchased'], 
               label='Purchased (Upward)', alpha=0.7, color='red')
        ax.bar(x, -zone_stats.loc[zones, 'volumessold'], 
               label='Sold (Downward)', alpha=0.7, color='blue')
        
        ax.set_xlabel('Zone')
        ax.set_ylabel('Volume (MWh)')
        ax.set_title(f'MSD Balancing Volumes by Zone - {date_str}', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(zones)
        ax.legend()
        ax.axhline(y=0, color='black', linewidth=0.5)
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/msd_zone_volumes.png', dpi=200)
        print(f"\n  Saved: {output_dir}/msd_zone_volumes.png")
        plt.close()
    
    # Plot 2: Hourly pattern
    fig, ax = plt.subplots(figsize=(14, 6))
    hours = hourly.index
    
    ax.plot(hours, hourly['volumespurchased'], marker='o', 
            label='Purchased (Upward)', color='red', linewidth=2)
    ax.plot(hours, hourly['volumessold'], marker='s', 
            label='Sold (Downward)', color='blue', linewidth=2)
    
    ax.set_xlabel('Hour')
    ax.set_ylabel('Volume (MWh)')
    ax.set_title(f'MSD Hourly Balancing Pattern - {date_str}', fontweight='bold')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_xticks(range(1, 25))
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/msd_hourly_pattern.png', dpi=200)
    print(f"  Saved: {output_dir}/msd_hourly_pattern.png")
    plt.close()


def analyze_mb(mb_file, output_dir, date_str):
    """Analyze MB (real-time balancing) data."""
    
    print("\n=== MB BALANCING ANALYSIS ===\n")
    
    # Load data
    mb = pd.read_csv(mb_file)
    mb.columns = [c.lower() for c in mb.columns]
    
    print(f"Total MB records: {len(mb)}")
    print(f"\nColumns: {list(mb.columns)}")
    
    # Service type breakdown
    if 'servicetype' in mb.columns:
        print("\nService types:")
        print(mb['servicetype'].value_counts())
    
    # Zone distribution
    if 'zone' in mb.columns:
        print("\nZone distribution:")
        print(mb.groupby('zone').size().sort_values(ascending=False))


def main():
    parser = argparse.ArgumentParser(description='Analyze MSD/MB balancing markets')
    parser.add_argument('--date', type=str, required=True,
                       help='Date to analyze (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Paths
    base_dir = Path(__file__).parent
    data_dir = base_dir / "data"
    output_dir = base_dir / "analysis"
    
    date_clean = args.date.replace('-', '')
    
    msd_file = data_dir / f"MSD_ME_MSDExAnteResults_{args.date}.csv"
    mb_file = data_dir / f"MB_ME_MBResults_{args.date}.csv"
    mgp_file = data_dir / f"MGP_ME_ZonalPrices_{args.date}.csv"
    
    # Check files exist
    if not msd_file.exists():
        print(f"Error: MSD file not found: {msd_file}")
        return
    
    if not mgp_file.exists():
        print(f"Error: MGP file not found: {mgp_file}")
        return
    
    # Analyze MSD
    analyze_msd(str(msd_file), str(mgp_file), str(output_dir), args.date)
    
    # Analyze MB if available
    if mb_file.exists():
        analyze_mb(str(mb_file), str(output_dir), args.date)
    else:
        print(f"\nWarning: MB file not found: {mb_file}")
    
    print("\n✅ Balancing analysis complete!\n")


if __name__ == "__main__":
    main()
