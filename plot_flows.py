"""
GME Flow Visualization

Visualize inter-zonal power flows with utilization coloring

Usage:
    python plot_flows.py --hour 12
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from plotting.plotter import GMEPlotter


def main():
    parser = argparse.ArgumentParser(description='Plot GME transmission flows')
    parser.add_argument('--hour', type=int, default=12,
                       help='Hour to plot (1-24, default: 12)')
    parser.add_argument('--date', type=str, default='2025-12-30',
                       help='Date to plot (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, default='mgp_flows.png',
                       help='Output filename')
    
    args = parser.parse_args()
    
    # Paths
    base_dir = Path(__file__).parent
    network_path = base_dir / "data_pypsa_eur_zonal"
    date_str = args.date.replace('-', '-')  # Keep dashes for now, files use dashes
    price_csv = base_dir / f"data/MGP_ME_ZonalPrices_{date_str}.csv"
    flow_csv = base_dir / f"data/MGP_ME_Transits_{date_str}.csv"
    
    # Check files exist
    for f in [price_csv, flow_csv]:
        if not f.exists():
            print(f"Error: File not found: {f}")
            sys.exit(1)
    
    print(f"=== GME Flow Visualization (Hour {args.hour}) ===\n")
    
    # Create plotter and generate flow plot
    plotter = GMEPlotter(str(network_path))
    plotter.load_network()
    plotter.load_market_data(str(price_csv))
    plotter.load_flow_data(str(flow_csv))
    plotter.plot_flows(hour=args.hour, output_file=args.output)
    
    print(f"\n✅ Done! Flow plot saved to: {args.output}")


if __name__ == "__main__":
    main()
