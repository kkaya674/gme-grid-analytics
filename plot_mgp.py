import pypsa
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import os

def plot_mgp_data(network_path, price_csv, limit_csv, hour=12):
    # Load the zonal network
    n = pypsa.Network(network_path)
    
    # Load price data
    try:
        prices = pd.read_csv(price_csv)
        # Filter for specific hour
        prices_at_h = prices[prices.Hour == hour].set_index('Zone')['Price']
    except Exception as e:
        print(f"Error loading prices: {e}")
        return

    # Load transmission limits
    try:
        limits = pd.read_csv(limit_csv)
        limits_at_h = limits[limits.Hour == hour]
    except Exception as e:
        print(f"Error loading limits: {e}")
        return

    # Update bus prices for plotting
    # Match zone names in price CSV with bus names in Network
    n.buses['marginal_price'] = prices_at_h
    
    # Update line capacities for plotting
    # In aggregated network, lines are named after connected buses usually, or have bus0, bus1
    # We need to match 'From' and 'To' in limits_csv with n.lines.bus0 and n.lines.bus1
    
    for idx, row in limits_at_h.iterrows():
        # Find line between From and To
        mask = ((n.lines.bus0 == row['From']) & (n.lines.bus1 == row['To'])) | \
               ((n.lines.bus0 == row['To']) & (n.lines.bus1 == row['From']))
        
        if mask.any():
            # Use the max of both directions for line width representation
            capacity = max(row['MaxTransmissionLimitFrom'], row['MaxTransmissionLimitTo'])
            n.lines.loc[mask, 's_nom'] = capacity
        else:
            # If line doesn't exist in network but exists in limits, we might want to add it?
            # For now, just skip or warn
            pass

    # Plot
    fig, ax = plt.subplots(figsize=(10, 12), subplot_kw={'projection': ccrs.PlateCarree()})
    
    # Add map features
    import cartopy.feature as cfeature
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.COASTLINE)
    ax.set_extent([6, 20, 36, 48], crs=ccrs.PlateCarree())

    # Plot network
    # Nodes colored by price, lines width by capacity
    try:
        from pypsa.plot import plot as plot_network
    except ImportError:
        try:
            from pypsa.plot import plot_network
        except ImportError:
            def plot_network(*args, **kwargs):
                print("PyPSA plot function not found. Please check your installation.")
                return None

    plot_network(
        n,
        ax=ax,
        bus_colors=n.buses.marginal_price,
        bus_cmap='viridis',
        line_widths=n.lines.s_nom / 1000 + 1,
        line_colors='gray'
    )
    ax.set_title(f"MGP Zonal Prices and Transmission Limits (Hour {hour})")
    
    # Add colorbar for prices
    sm = plt.cm.ScalarMappable(cmap='viridis', norm=plt.Normalize(vmin=n.buses.marginal_price.min(), vmax=n.buses.marginal_price.max()))
    plt.colorbar(sm, ax=ax, label='Price [EUR/MWh]', orientation='horizontal', pad=0.05, shrink=0.8)

    plt.savefig("mgp_plot.png", dpi=300, bbox_inches='tight')
    print("Plot saved as mgp_plot.png")
    plt.show()

if __name__ == "__main__":
    network_path = "/Users/kkaya674/Desktop/CodeSuite/gme_api/data_zonal"
    price_csv = "/Users/kkaya674/Desktop/CodeSuite/gme_api/data/MGP_ME_ZonalPrices_2024-12-30.csv"
    limit_csv = "/Users/kkaya674/Desktop/CodeSuite/gme_api/data/MGP_ME_TransmissionLimits_2024-12-30.csv"
    
    plot_mgp_data(network_path, price_csv, limit_csv)
