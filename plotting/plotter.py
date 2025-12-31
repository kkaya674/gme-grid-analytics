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
        self.flows_df = None
        
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
    
    def load_flow_data(self, flow_csv):
        """
        Load GME transmission flow data.
        
        Args:
            flow_csv: Path to flow CSV file (ME_Transits format)
            
        Returns:
            DataFrame with flow data
        """
        print(f"Loading flow data from {flow_csv}...")
        df = pd.read_csv(flow_csv)
        df.columns = [c.strip().lower() for c in df.columns]
        self.flows_df = df
        print(f"  Loaded {len(df)} flow records")
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
    
    def plot_flows(self, hour=12, output_file='gme_flows.png'):
        """
        Plot transmission flows for a specific hour.
        
        Args:
            hour: Hour to plot (1-24)
            output_file: Output filename
        """
        if self.network is None or self.prices_df is None or self.flows_df is None:
            raise ValueError("Network, prices, and flows must be loaded first.")
        
        # Filter data for specific hour
        h_prices = self.prices_df[self.prices_df['hour'] == hour].set_index('zone')['price']
        h_flows = self.flows_df[self.flows_df['hour'] == hour]
        
        print(f"  Found {len(h_flows)} flows for hour {hour}")
        
        # Map prices to buses
        self.network.buses['marginal_price'] = 0.0
        for zone, price in h_prices.items():
            if zone in self.network.buses.index:
                self.network.buses.at[zone, 'marginal_price'] = price
            elif zone == 'PUN':
                it_zones = ['NORD', 'CNOR', 'CSUD', 'SUD', 'CALA', 'SICI', 'SARD']
                for itz in it_zones:
                    if itz in self.network.buses.index:
                        self.network.buses.at[itz, 'marginal_price'] = price
        
        # Load GME transmission limits for accurate utilization
        limit_csv = None
        if hasattr(self, 'prices_df') and self.prices_df is not None:
            # Try to find limits file based on price CSV pattern
            from pathlib import Path
            import os
            # Assume limits file exists alongside prices
            for possible_dir in ['data', '../data', './']:
                test_path = Path(possible_dir) / f"MGP_ME_TransmissionLimits_{h_flows['flowdate'].iloc[0] if 'flowdate' in h_flows.columns else '2025-12-30'}.csv"
                if test_path.exists():
                    limit_csv = str(test_path)
                    break
        
        if limit_csv and Path(limit_csv).exists():
            gme_limits = pd.read_csv(limit_csv)
            gme_limits.columns = [c.strip().lower() for c in gme_limits.columns]
            print(f"  Using GME transmission limits from {limit_csv}")
        else:
            gme_limits = None
            print(f"  ⚠️  GME limits not found, using PyPSA s_nom (underestimates congestion)")
        
        for _, row in h_flows.iterrows():
            from_zone = str(row['from']).strip()
            to_zone = str(row['to']).strip()
            transit = float(row['transit'])
            h = int(row['hour'])
            p = int(row['period']) if 'period' in row else 1
            
            # Find matching line (bidirectional)
            mask = ((self.network.lines.bus0 == from_zone) & (self.network.lines.bus1 == to_zone)) | \
                   ((self.network.lines.bus0 == to_zone) & (self.network.lines.bus1 == from_zone))
            
            if mask.any():
                line_idx = self.network.lines[mask].index[0]
                self.network.lines.at[line_idx, 'flow'] = abs(transit)
                
                # Use GME limit if available, otherwise fall back to s_nom
                capacity = self.network.lines.at[line_idx, 's_nom']
                if gme_limits is not None:
                    limit_row = gme_limits[
                        (gme_limits['from'] == from_zone) & 
                        (gme_limits['to'] == to_zone) & 
                        (gme_limits['hour'] == h) &
                        (gme_limits['period'] == p)
                    ]
                    if len(limit_row) > 0:
                        capacity = limit_row['maxtransmissionlimitfrom'].iloc[0]
                
                if capacity > 0:
                    self.network.lines.at[line_idx, 'utilization'] = abs(transit) / capacity * 100
        
        # Create plot
        print("\nGenerating flow plot...")
        fig = plt.figure(figsize=(14, 10))
        ax = plt.axes(projection=ccrs.PlateCarree())
        
        ax.add_feature(cfeature.LAND, facecolor='lightgray')
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linewidth=0.5)
        ax.set_extent([6, 21, 35, 49], crs=ccrs.PlateCarree())
        
        # Import plot_network
        try:
            from pypsa.plot import plot_network
        except ImportError:
            try:
                from pypsa.plot.maps.static import plot_network
            except ImportError:
                from pypsa.plot import plot as plot_network
        
        # Use utilization for coloring lines (green to red)
        line_colors = self.network.lines.utilization.fillna(0)
        
        plot_network(
            self.network,
            ax=ax,
            bus_colors=self.network.buses.marginal_price,
            bus_cmap='viridis',
            line_widths=(self.network.lines.flow / 500 + 1),  # Size by flow
            line_colors=line_colors,
            line_cmap='RdYlGn_r',  # Red = high utilization, green = low
            bus_sizes=0.01
        )
        
        # Add labels
        for idx, row in self.network.buses.iterrows():
            if row.marginal_price > 0:
                ax.text(row.x, row.y, f"{idx}\n€{row.marginal_price:.1f}",
                       fontsize=8, ha='center', va='bottom',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
        
        market_name = self._get_market_name()
        plt.title(f"GME {market_name} Flows (Hour {hour})", fontsize=14, fontweight='bold')
        
        # Price colorbar
        sm_price = plt.cm.ScalarMappable(cmap='viridis', 
                                         norm=plt.Normalize(vmin=self.network.buses.marginal_price.min(), 
                                                           vmax=self.network.buses.marginal_price.max()))
        sm_price.set_array([])
        cbar_price = plt.colorbar(sm_price, ax=ax, orientation='vertical', pad=0.02, fraction=0.03, location='left')
        cbar_price.set_label('Price (€/MWh)', fontsize=10)
        
        # Utilization colorbar
        sm_util = plt.cm.ScalarMappable(cmap='RdYlGn_r',
                                        norm=plt.Normalize(vmin=0, vmax=100))
        sm_util.set_array([])
        cbar_util = plt.colorbar(sm_util, ax=ax, orientation='vertical', pad=0.02, fraction=0.03)
        cbar_util.set_label('Line Utilization (%)', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Flow plot saved: {output_file}")
        
        return fig
    
    def _get_market_name(self):
        """Extract market name from loaded data."""
        if self.prices_df is not None and 'market' in self.prices_df.columns:
            return self.prices_df['market'].iloc[0]
        return "Market"
