import pypsa
import pandas as pd
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

    # Map limits to lines
    # Aggregated network lines might be differently named. 
    # Usually they connect the same zones if from/to matches bus names.
    n.lines['s_nom'] = 1.0 # Default fallback width
    
    for idx, row in h_limits.iterrows():
        f_zone = str(row['from']).strip()
        t_zone = str(row['to']).strip()
        
        # In PyPSA network, checks lines between these buses
        mask = ((n.lines.bus0 == f_zone) & (n.lines.bus1 == t_zone)) | \
               ((n.lines.bus0 == t_zone) & (n.lines.bus1 == f_zone))
        
        if mask.any():
            cap = max(float(row['maxtransmissionlimitfrom']), float(row['maxtransmissionlimitto']))
            n.lines.loc[mask, 's_nom'] = cap
            print(f"Line {f_zone}-{t_zone} capacity set to {cap} MW")

    # Final Plotting
    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw={'projection': ccrs.PlateCarree()})
    
    ax.add_feature(cfeature.BORDERS, linestyle='-', alpha=0.5)
    ax.add_feature(cfeature.COASTLINE, alpha=0.5)
    ax.add_feature(cfeature.LAND, facecolor='#f9f9f9')
    ax.set_extent([6, 20, 36, 48], crs=ccrs.PlateCarree())

    # Try different plot functions as per PyPSA version
    try:
        from pypsa.plot import plot as plot_network
    except ImportError:
        try:
            from pypsa.plot import plot_network
        except ImportError:
            print("Could not find PyPSA plot function.")
            return

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
    for bus, row in n.buses.iterrows():
        ax.text(row.x, row.y + 0.2, f"{bus}\n{row.marginal_price:.1f}", 
                ha='center', va='bottom', fontsize=8, fontweight='bold',
                transform=ccrs.PlateCarree(), bbox=dict(facecolor='white', alpha=0.6, pad=1))

    ax.set_title(f"GME MGP Zonal Prices [EUR/MWh] and Transmission Limits [MW]\n2024-12-30 Hour {hour}", fontsize=14)
    
    plt.savefig("mgp_plot.png", dpi=300, bbox_inches='tight')
    print("Plot successfully generated: mgp_plot.png")
    # plt.show() # Disabled for headless run

if __name__ == "__main__":
    base_dir = "/Users/kkaya674/Desktop/CodeSuite/gme_api"
    network_path = os.path.join(base_dir, "data_italy/zonal")
    price_csv = os.path.join(base_dir, "data/MGP_ME_ZonalPrices_2025-12-30.csv")
    limit_csv = os.path.join(base_dir, "data/MGP_ME_TransmissionLimits_2025-12-30.csv")
    
    plot_mgp_data(network_path, price_csv, limit_csv)
