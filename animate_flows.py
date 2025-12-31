"""
GME Animated Flow Visualization

Create animated GIF showing 24-hour flow evolution (96 sessions)

Usage:
    python animate_flows.py --date 2025-12-30 --output mgp_animation.gif
"""

import argparse
import os
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

sys.path.insert(0, str(Path(__file__).parent))

from plotting.plotter import GMEPlotter
import pandas as pd


def create_animation(network_path, price_csv, flow_csv, output_file='mgp_animation.gif'):
    """
    Create animated GIF of flow evolution.
    
    Args:
        network_path: Path to PyPSA-Eur zonal network
        price_csv: Path to price CSV
        flow_csv: Path to flow CSV
        output_file: Output GIF filename
    """
    print("=== GME Flow Animation (96 Sessions) ===\n")
    
    # Load plotter
    plotter = GMEPlotter(network_path)
    plotter.load_network()
    plotter.load_market_data(price_csv)
    plotter.load_flow_data(flow_csv)
    
    # Get unique hour-period combinations (24 hours × 4 periods)
    sessions = plotter.flows_df[['hour', 'period']].drop_duplicates().sort_values(['hour', 'period'])
    print(f"Found {len(sessions)} sessions")
    
    if len(sessions) < 96:
        print(f"Warning: Expected 96 sessions, found {len(sessions)}")
    
    # Create figure
    fig = plt.figure(figsize=(14, 10))
    
    def update_frame(frame_idx):
        """Update function for each animation frame."""
        plt.clf()
        ax = plt.axes(projection=ccrs.PlateCarree())
        
        # Get current session
        session = sessions.iloc[frame_idx]
        hour = int(session['hour'])
        period = int(session['period'])
        
        # Filter data for this session
        h_prices = plotter.prices_df[
            (plotter.prices_df['hour'] == hour) & 
            (plotter.prices_df['period'] == period)
        ].set_index('zone')['price']
        
        h_flows = plotter.flows_df[
            (plotter.flows_df['hour'] == hour) & 
            (plotter.flows_df['period'] == period)
        ]
        
        # Map prices to buses
        plotter.network.buses['marginal_price'] = 0.0
        for zone, price in h_prices.items():
            if zone in plotter.network.buses.index:
                plotter.network.buses.at[zone, 'marginal_price'] = price
            elif zone == 'PUN':
                it_zones = ['NORD', 'CNOR', 'CSUD', 'SUD', 'CALA', 'SICI', 'SARD']
                for itz in it_zones:
                    if itz in plotter.network.buses.index:
                        plotter.network.buses.at[itz, 'marginal_price'] = price
        
        # Map flows to lines
        plotter.network.lines['flow'] = 0.0
        plotter.network.lines['utilization'] = 0.0
        
        for _, row in h_flows.iterrows():
            from_zone = str(row['from']).strip()
            to_zone = str(row['to']).strip()
            transit = float(row['transit'])
            
            mask = ((plotter.network.lines.bus0 == from_zone) & (plotter.network.lines.bus1 == to_zone)) | \
                   ((plotter.network.lines.bus0 == to_zone) & (plotter.network.lines.bus1 == from_zone))
            
            if mask.any():
                line_idx = plotter.network.lines[mask].index[0]
                plotter.network.lines.at[line_idx, 'flow'] = abs(transit)
                capacity = plotter.network.lines.at[line_idx, 's_nom']
                if capacity > 0:
                    plotter.network.lines.at[line_idx, 'utilization'] = abs(transit) / capacity * 100
        
        # Plot
        ax.add_feature(cfeature.LAND, facecolor='lightgray')
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linewidth=0.8, edgecolor='black')
        ax.set_extent([6, 21, 35, 49], crs=ccrs.PlateCarree())
        
        # Add gridlines
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.3)
        gl.top_labels = False
        gl.right_labels = False
        
        try:
            from pypsa.plot import plot_network
        except ImportError:
            try:
                from pypsa.plot.maps.static import plot_network
            except ImportError:
                from pypsa.plot import plot as plot_network
        
        line_colors = plotter.network.lines.utilization.fillna(0)
        
        plot_network(
            plotter.network,
            ax=ax,
            bus_colors=plotter.network.buses.marginal_price,
            bus_cmap='viridis',
            line_widths=(plotter.network.lines.flow / 500 + 1),
            line_colors=line_colors,
            line_cmap='RdYlGn_r',
            bus_sizes=0.01
        )
        
        # Add zone labels with prices
        for idx, row in plotter.network.buses.iterrows():
            price = row.marginal_price
            if price > 0:
                label_text = f"{idx}\n€{price:.1f}"
            else:
                label_text = idx
            
            ax.text(row.x, row.y + 0.3, label_text,
                   fontsize=8, ha='center', va='bottom', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                            edgecolor='black', alpha=0.85, linewidth=0.5))
        
        # Title with session info
        plt.title(f"GME MGP Flows | Hour {hour:02d} Session {period} ({frame_idx+1}/96)", 
                 fontsize=14, fontweight='bold')
        
        # Colorbars
        from matplotlib import cm
        import matplotlib as mpl
        
        # Price colorbar
        price_min = plotter.prices_df['price'].min()
        price_max = plotter.prices_df['price'].max()
        sm_price = cm.ScalarMappable(cmap='viridis', 
                                     norm=mpl.colors.Normalize(vmin=price_min, vmax=price_max))
        sm_price.set_array([])
        cbar_price = plt.colorbar(sm_price, ax=ax, orientation='vertical', 
                                  pad=0.02, fraction=0.03, location='left')
        cbar_price.set_label('Price (€/MWh)', fontsize=10)
        
        # Utilization colorbar
        sm_util = cm.ScalarMappable(cmap='RdYlGn_r',
                                   norm=mpl.colors.Normalize(vmin=0, vmax=100))
        sm_util.set_array([])
        cbar_util = plt.colorbar(sm_util, ax=ax, orientation='vertical', 
                                pad=0.02, fraction=0.03)
        cbar_util.set_label('Utilization (%)', fontsize=10)
        
        print(f"Frame {frame_idx+1}/96 (H{hour:02d}P{period}) - {len(h_flows)} flows")
        
        return ax,
    
    # Create animation
    print("\nGenerating animation frames...")
    anim = animation.FuncAnimation(
        fig, 
        update_frame, 
        frames=len(sessions),
        interval=200,  # 200ms per frame
        repeat=True,
        blit=False
    )
    
    # Save as GIF
    print(f"Saving animation to {output_file}...")
    anim.save(output_file, writer='pillow', fps=5, dpi=150)
    print(f"✅ Animation saved: {output_file}")
    
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Create GME flow animation')
    parser.add_argument('--date', type=str, default='2025-12-30',
                       help='Date to animate (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, default='mgp_flow_animation.gif',
                       help='Output GIF filename')
    
    args = parser.parse_args()
    
    # Paths
    base_dir = Path(__file__).parent
    network_path = base_dir / "data_pypsa_eur_zonal"
    date_str = args.date
    price_csv = base_dir / f"data/MGP_ME_ZonalPrices_{date_str}.csv"
    flow_csv = base_dir / f"data/MGP_ME_Transits_{date_str}.csv"
    
    # Check files exist
    for f in [price_csv, flow_csv]:
        if not f.exists():
            print(f"Error: File not found: {f}")
            sys.exit(1)
    
    create_animation(str(network_path), str(price_csv), str(flow_csv), args.output)


if __name__ == "__main__":
    main()
