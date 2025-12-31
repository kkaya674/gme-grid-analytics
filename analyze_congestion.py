"""
GME Congestion Analysis

Analyze transmission congestion patterns and correlations with generator locations

Usage:
    python analyze_congestion.py --date 2025-12-30
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

def analyze_congestion(flow_csv, price_csv, output_dir='analysis'):
    """
    Analyze congestion patterns throughout the day.
    
    Args:
        flow_csv: Path to transit flow CSV
        price_csv: Path to zonal price CSV
        output_dir: Output directory for analysis results
    """
    print("=== GME Congestion Analysis ===\n")
    
    # Load data
    flows_df = pd.read_csv(flow_csv)
    prices_df = pd.read_csv(price_csv)
    
    flows_df.columns = [c.strip().lower() for c in flows_df.columns]
    prices_df.columns = [c.strip().lower() for c in prices_df.columns]
    
    # Load network for capacity data
    import pypsa
    network = pypsa.Network('data_pypsa_eur_zonal')
    
    # Calculate utilization for each flow
    flows_df['corridor'] = flows_df['from'] + '-' + flows_df['to']
    flows_df['abs_flow'] = flows_df['transit'].abs()
    
    # Map capacity to flows
    flows_df['capacity'] = 0.0
    for idx, row in flows_df.iterrows():
        from_zone = str(row['from']).strip()
        to_zone = str(row['to']).strip()
        
        mask = ((network.lines.bus0 == from_zone) & (network.lines.bus1 == to_zone)) | \
               ((network.lines.bus0 == to_zone) & (network.lines.bus1 == from_zone))
        
        if mask.any():
            flows_df.at[idx, 'capacity'] = network.lines[mask]['s_nom'].iloc[0]
    
    flows_df['utilization'] = (flows_df['abs_flow'] / flows_df['capacity'] * 100).fillna(0)
    
    Path(output_dir).mkdir(exist_ok=True)
    
    # Analysis 1: Top congested corridors
    print("\n1. TOP CONGESTED CORRIDORS (Average Utilization)")
    avg_util = flows_df.groupby('corridor')['utilization'].mean().sort_values(ascending=False).head(10)
    print(avg_util.to_string())
    
    # Analysis 2: Morning vs Midday pattern
    print("\n2. MORNING (07:00-10:00) vs MIDDAY (12:00-15:00) PATTERN")
    
    morning_flows = flows_df[flows_df['hour'].between(7, 10)]
    midday_flows = flows_df[flows_df['hour'].between(12, 15)]
    
    print("\nMorning peak - Top 5 congested:")
    morning_top = morning_flows.groupby('corridor')['utilization'].mean().sort_values(ascending=False).head(5)
    print(morning_top.to_string())
    
    print("\nMidday solar peak - Top 5 congested:")
    midday_top = midday_flows.groupby('corridor')['utilization'].mean().sort_values(ascending=False).head(5)
    print(midday_top.to_string())
    
    # Analysis 3: North vs South flow direction
    print("\n3. NORTH-SOUTH FLOW PATTERNS")
    
    # Define north/south corridors
    north_south_corridors = [
        'NORD-CNOR', 'CNOR-NORD',
        'CNOR-CSUD', 'CSUD-CNOR',
        'CSUD-SUD', 'SUD-CSUD',
        'SUD-CALA', 'CALA-SUD',
        'NORD-SVIZ', 'SVIZ-NORD'
    ]
    
    ns_flows = flows_df[flows_df['corridor'].isin(north_south_corridors)]
    
    # Group by hour
    hourly_ns = ns_flows.groupby('hour').agg({
        'abs_flow': 'mean',
        'utilization': 'mean'
    })
    
    print("\nHourly North-South corridor activity:")
    print(hourly_ns.to_string())
    
    # Visualization 1: Heatmap of utilization by hour and corridor
    print("\n4. GENERATING VISUALIZATIONS...")
    
    pivot_util = flows_df.pivot_table(
        values='utilization',
        index='corridor',
        columns='hour',
        aggfunc='mean'
    )
    
    top_corridors = avg_util.head(15).index
    pivot_top = pivot_util.loc[pivot_util.index.intersection(top_corridors)]
    
    fig, ax = plt.subplots(figsize=(16, 10))
    sns.heatmap(pivot_top, cmap='RdYlGn_r', center=50, vmin=0, vmax=100,
                annot=False, fmt='.0f', cbar_kws={'label': 'Utilization (%)'})
    plt.title('Hourly Utilization Heatmap - Top Congested Corridors', fontsize=14, fontweight='bold')
    plt.xlabel('Hour')
    plt.ylabel('Corridor')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/congestion_heatmap.png', dpi=200)
    print(f"  Saved: {output_dir}/congestion_heatmap.png")
    plt.close()
    
    # Visualization 2: Morning vs midday comparison
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    morning_top.plot(kind='barh', ax=axes[0], color='orange')
    axes[0].set_title('Morning Peak (07:00-10:00)', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Avg Utilization (%)')
    axes[0].set_xlim(0, 100)
    
    midday_top.plot(kind='barh', ax=axes[1], color='gold')
    axes[1].set_title('Midday Solar Peak (12:00-15:00)', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Avg Utilization (%)')
    axes[1].set_xlim(0, 100)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/morning_vs_midday.png', dpi=200)
    print(f"  Saved: {output_dir}/morning_vs_midday.png")
    plt.close()
    
    # Visualization 3: Time series of key corridors
    key_corridors = ['NORD-CNOR', 'CNOR-CSUD', 'CSUD-SUD', 'SUD-CALA']
    
    fig, ax = plt.subplots(figsize=(14, 6))
    for corridor in key_corridors:
        if corridor in flows_df['corridor'].values:
            corridor_data = flows_df[flows_df['corridor'] == corridor]
            hourly = corridor_data.groupby('hour')['utilization'].mean()
            ax.plot(hourly.index, hourly.values, marker='o', label=corridor, linewidth=2)
    
    ax.axvspan(7, 10, alpha=0.2, color='orange', label='Morning Peak')
    ax.axvspan(12, 15, alpha=0.2, color='gold', label='Solar Peak')
    ax.set_xlabel('Hour')
    ax.set_ylabel('Utilization (%)')
    ax.set_title('North-South Corridor Utilization Throughout Day', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 100)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/corridor_timeseries.png', dpi=200)
    print(f"  Saved: {output_dir}/corridor_timeseries.png")
    plt.close()
    
    # Analysis 4: Price spread correlation
    print("\n5. PRICE SPREAD vs CONGESTION CORRELATION")
    
    # Calculate north-south price spread
    north_prices = prices_df[prices_df['zone'] == 'NORD'].groupby('hour')['price'].mean()
    south_prices = prices_df[prices_df['zone'].isin(['SUD', 'CALA'])].groupby('hour')['price'].mean()
    price_spread = (south_prices - north_prices).fillna(0)
    
    # Correlate with NS corridor utilization
    print("\nNorth-South price spread by hour:")
    print(price_spread.to_string())
    
    print("\n✅ Analysis complete!")
    print(f"\nResults saved to {output_dir}/")
    
    return flows_df


def main():
    parser = argparse.ArgumentParser(description='Analyze GME congestion patterns')
    parser.add_argument('--date', type=str, default='2025-12-30',
                       help='Date to analyze (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, default='analysis',
                       help='Output directory')
    
    args = parser.parse_args()
    
    # Paths
    date_str = args.date
    flow_csv = f"data/MGP_ME_Transits_{date_str}.csv"
    price_csv = f"data/MGP_ME_ZonalPrices_{date_str}.csv"
    
    if not Path(flow_csv).exists() or not Path(price_csv).exists():
        print(f"Error: Data files not found for {date_str}")
        sys.exit(1)
    
    analyze_congestion(flow_csv, price_csv, args.output)


if __name__ == "__main__":
    main()
