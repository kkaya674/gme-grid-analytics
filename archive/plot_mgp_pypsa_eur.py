"""
Plot GME MGP Data on PyPSA-Eur Zonal Network
Shows zonal prices and transmission limits for Italy + neighbors
"""

import pandas as pd
import pypsa
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import os
import cartopy.feature as cfeature
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

def plot_mgp_data(network_path, price_csv, limit_csv, hour=12):
    print(f"Loading zonal network from {network_path}...")
    n = pypsa.Network(network_path)
    
    print(f"Loading MGP prices from {price_csv} for hour {hour}...")
    try:
        prices_df = pd.read_csv(price_csv)
        # GME data might have spaces or mixed case
        prices_df.columns = [c.strip().lower() for c in prices_df.columns]
        h_prices = prices_df[prices_df['hour'] == hour].set_index('zone')['price']
        print(f"Found {len(h_prices)} zonal prices.")
    except Exception as e:
        print(f"Error processing prices: {e}")
        return

    print(f"Loading MGP transmission limits from {limit_csv} for hour {hour}...")
    try:
        limits_df = pd.read_csv(limit_csv)
        limits_df.columns = [c.strip().lower() for c in limits_df.columns]
        h_limits = limits_df[limits_df['hour'] == hour]
        print(f"Found {len(h_limits)} transmission limits.")
    except Exception as e:
        print(f"Error processing limits: {e}")
        return

    # Map prices to buses
    n.buses['marginal_price'] = 0.0
    for zone, price in h_prices.items():
        if zone in n.buses.index:
            n.buses.at[zone, 'marginal_price'] = price
        else:
            # Maybe map PUN to all IT zones if it's there
            if zone == 'PUN':
                it_zones = ['NORD', 'CNOR', 'CSUD', 'SUD', 'CALA', 'SICI', 'SARD']
                for itz in it_zones:
                    if itz in n.buses.index and n.buses.at[itz, 'marginal_price'] == 0:
                        n.buses.at[itz, 'marginal_price'] = price

    # Use PyPSA-Eur line capacities (s_nom) - these are already in the network
    # GME limits are market-based, not physical capacities
    print(f"\nUsing PyPSA-Eur line capacities (s_nom):")
    for idx, row in n.lines.iterrows():
        print(f"  {idx}: {row.s_nom:.0f} MW ({row.n_lines} lines aggregated)")

    # Plotting
    print("\nGenerating plot...")
    fig = plt.figure(figsize=(14, 10))
    ax = plt.axes(projection=ccrs.PlateCarree())
    
    # Map background
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    
    # Set extent to Italy + neighbors
    ax.set_extent([6, 21, 35, 49], crs=ccrs.PlateCarree())
    
    # Import plot_network with fallback
    try:
        from pypsa.plot import plot_network
    except ImportError:
        try:
            from pypsa.plot.maps.static import plot_network
        except ImportError:
            from pypsa.plot import plot as plot_network
    
    plot_network(
        n,
        ax=ax,
        bus_colors=n.buses.marginal_price,
        bus_cmap='viridis',
        line_widths=n.lines.s_nom / 1000 + 1,
        line_colors='gray',
        bus_sizes=0.01  # Much smaller nodes
    )
    
    # Add text labels for prices
    for idx, row in n.buses.iterrows():
        if row.marginal_price > 0:
            ax.text(row.x, row.y, f"{idx}\n€{row.marginal_price:.1f}",
                   fontsize=8, ha='center', va='bottom',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    plt.title(f"GME MGP Prices & Transmission Limits (Hour {hour})", fontsize=14, fontweight='bold')
    
    # Color bar
    sm = plt.cm.ScalarMappable(cmap='viridis', 
                               norm=plt.Normalize(vmin=n.buses.marginal_price.min(), 
                                                 vmax=n.buses.marginal_price.max()))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, fraction=0.03)
    cbar.set_label('Price (€/MWh)', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('mgp_plot_pypsa_eur.png', dpi=300, bbox_inches='tight')
    print(f"Plot successfully generated: mgp_plot_pypsa_eur.png")

if __name__ == "__main__":
    base_dir = "/Users/kkaya674/Desktop/CodeSuite/gme_api"
    network_path = os.path.join(base_dir, "data_pypsa_eur_zonal")
    price_csv = os.path.join(base_dir, "data/MGP_ME_ZonalPrices_2025-12-30.csv")
    limit_csv = os.path.join(base_dir, "data/MGP_ME_TransmissionLimits_2025-12-30.csv")
    
    plot_mgp_data(network_path, price_csv, limit_csv)
