"""
GME Market Visualization CLI

Usage:
    python plot_gme.py --market MGP --hour 12
    python plot_gme.py --market MB --hour 12 --date 2025-12-30
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from plotting.plotter import GMEPlotter
from plotting.utils import get_latest_data_file, format_market_name


def main():
    parser = argparse.ArgumentParser(description='Plot GME market data')
    parser.add_argument('--market', type=str, required=True, 
                       choices=['MGP', 'MB', 'MSD'],
                       help='Market to plot (MGP/MB/MSD)')
    parser.add_argument('--hour', type=int, default=12,
                       help='Hour to plot (1-24, default: 12)')
    parser.add_argument('--date', type=str, default=None,
                       help='Date to plot (YYYY-MM-DD, default: latest)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output filename (default: {market}_plot.png)')
    
    args = parser.parse_args()
    
    # Paths
    base_dir = Path(__file__).parent.parent
    network_path = base_dir / "data/network/data_pypsa_eur_zonal"
    data_dir = base_dir / "workspace"
    
    # Find data file
    if args.date:
        price_file = data_dir / f"{args.market}_ME_ZonalPrices_{args.date}.csv"
    else:
        price_file = get_latest_data_file(str(data_dir), args.market, "ME_ZonalPrices")
    
    if not price_file or not os.path.exists(price_file):
        print(f"Error: No data file found for {args.market}")
        print(f"  Expected: {price_file}")
        sys.exit(1)
    
    # Output filename
    output_file = args.output or f"{args.market.lower()}_plot.png"
    
    # Create plotter and generate plot
    print(f"=== GME {format_market_name(args.market)} Visualization ===\n")
    
    plotter = GMEPlotter(str(network_path))
    plotter.load_network()
    plotter.load_market_data(str(price_file))
    
    # Extract date from loaded data
    date_str = args.date if args.date else plotter.prices_df['flowdate'].iloc[0] if 'flowdate' in plotter.prices_df.columns else 'Unknown'
    
    plotter.plot_market(hour=args.hour, output_file=output_file)
    
    print(f"\n✅ Done! Plot saved to: {output_file}")


if __name__ == "__main__":
    main()
