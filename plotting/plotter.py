"""
GME Market Plotter - Generic visualization for all GME markets
"""

import pandas as pd
import pypsa
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
import ssl
ssl._create_default_https_context = ssl._create_unverified_context


class GMEPlotter:
    """Generic plotter for GME market data visualization."""
    
    def __init__(self, network_path):
        """
        Initialize plotter with network path.
        
        Args:
            network_path: Path to PyPSA-Eur zonal network directory
        """
        self.network_path = network_path
        self.network = None
        self.prices_df = None
        
    def load_network(self):
        """Load PyPSA-Eur zonal network."""
        print(f"Loading zonal network from {self.network_path}...")
        self.network = pypsa.Network(self.network_path)
        print(f"  Loaded {len(self.network.buses)} buses, {len(self.network.lines)} lines")
        return self.network
    
    def load_market_data(self, price_csv):
        """
        Load GME market price data.
        
        Args:
            price_csv: Path to price CSV file (ME_ZonalPrices format)
            
        Returns:
            DataFrame with price data
        """
        print(f"Loading market data from {price_csv}...")
        df = pd.read_csv(price_csv)
        df.columns = [c.strip().lower() for c in df.columns]
        self.prices_df = df
        print(f"  Loaded {len(df)} price records")
        return df
    
    def plot_market(self, hour=12, output_file='gme_plot.png'):
        """
        Plot market data for a specific hour.
        
        Args:
            hour: Hour to plot (1-24)
            output_file: Output filename
        """
        if self.network is None:
            raise ValueError("Network not loaded. Call load_network() first.")
        if self.prices_df is None:
            raise ValueError("Market data not loaded. Call load_market_data() first.")
        
        # Filter data for specific hour
        h_prices = self.prices_df[self.prices_df['hour'] == hour].set_index('zone')['price']
        print(f"  Found {len(h_prices)} zonal prices for hour {hour}")
        
        # Map prices to buses
        self.network.buses['marginal_price'] = 0.0
        for zone, price in h_prices.items():
            if zone in self.network.buses.index:
                self.network.buses.at[zone, 'marginal_price'] = price
            elif zone == 'PUN':
                # Map PUN to all Italian zones if necessary
                it_zones = ['NORD', 'CNOR', 'CSUD', 'SUD', 'CALA', 'SICI', 'SARD']
                for itz in it_zones:
                    if itz in self.network.buses.index and self.network.buses.at[itz, 'marginal_price'] == 0:
                        self.network.buses.at[itz, 'marginal_price'] = price
        
        # Create plot
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
        
        # Plot network
        plot_network(
            self.network,
            ax=ax,
            bus_colors=self.network.buses.marginal_price,
            bus_cmap='viridis',
            line_widths=self.network.lines.s_nom / 1000 + 1,
            line_colors='gray',
            bus_sizes=0.01
        )
        
        # Add text labels for prices
        for idx, row in self.network.buses.iterrows():
            if row.marginal_price > 0:
                ax.text(row.x, row.y, f"{idx}\n€{row.marginal_price:.1f}",
                       fontsize=8, ha='center', va='bottom',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        # Get market name from filename/data
        market_name = self._get_market_name()
        plt.title(f"GME {market_name} Prices (Hour {hour})", fontsize=14, fontweight='bold')
        
        # Color bar
        sm = plt.cm.ScalarMappable(cmap='viridis', 
                                   norm=plt.Normalize(vmin=self.network.buses.marginal_price.min(), 
                                                     vmax=self.network.buses.marginal_price.max()))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, fraction=0.03)
        cbar.set_label('Price (€/MWh)', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved: {output_file}")
        
        return fig
    
    def _get_market_name(self):
        """Extract market name from loaded data."""
        if 'market' in self.prices_df.columns:
            return self.prices_df['market'].iloc[0]
        return "Market"
