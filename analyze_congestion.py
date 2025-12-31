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
    
    # Filter to ONLY network corridors (exclude external borders)
    network_corridors = set()
    for idx, row in network.lines.iterrows():
        network_corridors.add(f"{row.bus0}-{row.bus1}")
        network_corridors.add(f"{row.bus1}-{row.bus0}")  # bidirectional
    
    # Filter flows to network corridors only
    network_flows = flows_df[flows_df['corridor'].isin(network_corridors)].copy()
    
    print(f"\nFiltered to {len(network_corridors)} network corridors:")
    print(f"  Total flow records: {len(flows_df)} → {len(network_flows)} (network only)")
    
    # Analysis 1: Top congested NETWORK corridors
    print("\n1. TOP CONGESTED NETWORK CORRIDORS (Average Utilization)")
    avg_util = network_flows.groupby('corridor')['utilization'].mean().sort_values(ascending=False).head(15)
    print(avg_util.to_string())
    
    # Analysis 2: Morning vs Midday pattern (NETWORK CORRIDORS ONLY)
    print("\n2. MORNING (07:00-10:00) vs MIDDAY (12:00-15:00) PATTERN")
    
    morning_flows = network_flows[network_flows['hour'].between(7, 10)]
    midday_flows = network_flows[network_flows['hour'].between(12, 15)]
    
    print("\nMorning peak - Top 10 congested:")
    morning_top = morning_flows.groupby('corridor')['utilization'].mean().sort_values(ascending=False).head(10)
    print(morning_top.to_string())
    
    print("\nMidday solar peak - Top 10 congested:")
    midday_top = midday_flows.groupby('corridor')['utilization'].mean().sort_values(ascending=False).head(10)
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
    
    pivot_util = network_flows.pivot_table(
        values='utilization',
        index='corridor',
        columns='hour',
        aggfunc='mean'
    )
    
    # Show all network corridors (no need to filter, already filtered)
    if len(avg_util) > 0:
        top_corridors = avg_util.head(15).index
        pivot_top = pivot_util.loc[pivot_util.index.intersection(top_corridors)]
        
        fig, ax = plt.subplots(figsize=(16, 10))
        sns.heatmap(pivot_top, cmap='RdYlGn_r', center=25, vmin=0, vmax=50,
                    annot=True, fmt='.1f', cbar_kws={'label': 'Utilization (%)'})
        plt.title('Hourly Utilization Heatmap - Network Corridors', fontsize=14, fontweight='bold')
        plt.xlabel('Hour')
        plt.ylabel('Corridor')
        plt.tight_layout()
        plt.savefig(f'{output_dir}/congestion_heatmap.png', dpi=200)
        print(f"  Saved: {output_dir}/congestion_heatmap.png")
        plt.close()
    
    # Visualization 2: Morning vs midday comparison
    # Filter out corridors with inf utilization (capacity = 0)
    morning_top_finite = morning_top[morning_top < float('inf')].head(5)
    midday_top_finite = midday_top[midday_top < float('inf')].head(5)
    
    if len(morning_top_finite) > 0 or len(midday_top_finite) > 0:
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        if len(morning_top_finite) > 0:
            morning_top_finite.plot(kind='barh', ax=axes[0], color='orange')
            axes[0].set_title('Morning Peak (07:00-10:00)', fontsize=12, fontweight='bold')
            axes[0].set_xlabel('Avg Utilization (%)')
            axes[0].set_xlim(0, min(100, morning_top_finite.max() * 1.1))
        else:
            axes[0].text(0.5, 0.5, 'No finite data', ha='center', va='center')
            axes[0].set_title('Morning Peak (07:00-10:00)', fontsize=12, fontweight='bold')
        
        if len(midday_top_finite) > 0:
            midday_top_finite.plot(kind='barh', ax=axes[1], color='gold')
            axes[1].set_title('Midday Solar Peak (12:00-15:00)', fontsize=12, fontweight='bold')
            axes[1].set_xlabel('Avg Utilization (%)')
            axes[1].set_xlim(0, min(100, midday_top_finite.max() * 1.1))
        else:
            axes[1].text(0.5, 0.5, 'No finite data', ha='center', va='center')
            axes[1].set_title('Midday Solar Peak (12:00-15:00)', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/morning_vs_midday.png', dpi=200)
        print(f"  Saved: {output_dir}/morning_vs_midday.png")
        plt.close()
    
    # Visualization 3: Time series of key corridors (use actual GME directions)
    key_corridors = ['CNOR-NORD', 'CNOR-CSUD', 'CSUD-SUD', 'CALA-SUD']
    
    fig, ax = plt.subplots(figsize=(14, 6))
    for corridor in key_corridors:
        if corridor in network_flows['corridor'].values:
            corridor_data = network_flows[network_flows['corridor'] == corridor]
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
