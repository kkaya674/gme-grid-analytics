# GME Market Visualization Pipeline

Python pipeline for visualizing Italian electricity market (GME) data with PyPSA-Eur network topology.

## Features

- 🔌 **Network Visualization**: PyPSA-Eur zonal network with Italian market zones
- 📊 **Price Mapping**: MGP, MSD, MB market prices on network topology  
- 🌊 **Flow Analysis**: Transmission flows with GME market limits
- 📈 **Congestion Analysis**: 96-session heatmaps showing 15-min granularity
- 🎬 **Animated Flows**: 24-hour evolution (96 frames)

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure GME Credentials

Create `.env` file with your GME API credentials:

```
GME_USERNAME=your_username
GME_PASSWORD=your_password
```

### 3. Fetch Market Data

```bash
# Fetch all market data for a date
python main.py --date 2025-12-30

# This fetches:
# - MGP prices (ME_ZonalPrices)
# - MGP flows (ME_Transits)
# - GME transmission limits (ME_TransmissionLimits)
# - MSD results (ME_MSDExAnteResults)
```

### 4. Generate Visualizations

```bash
# Static price plot
python plot_gme.py --date 2025-12-30 --hour 12

# Flow visualization
python plot_flows.py --date 2025-12-30 --hour 12

# Animated 24-hour flow evolution
python animate_flows.py --date 2025-12-30 --output mgp_animation.gif

# Congestion analysis (96-session heatmap + patterns)
python analyze_congestion.py --date 2025-12-30
```

## Data Pipeline

```
┌─────────────┐
│  GME API    │
│  (main.py)  │
└──────┬──────┘
       │
       ├─→ data/MGP_ME_ZonalPrices_YYYY-MM-DD.csv
       ├─→ data/MGP_ME_Transits_YYYY-MM-DD.csv
       ├─→ data/MGP_ME_TransmissionLimits_YYYY-MM-DD.csv
       └─→ data/MSD_ME_MSDExAnteResults_YYYY-MM-DD.csv
       
┌──────────────────┐
│  Visualization   │
└──────────────────┘
       │
       ├─→ plot_gme.py          (static prices)
       ├─→ plot_flows.py        (static flows)
       ├─→ animate_flows.py     (animated GIF)
       └─→ analyze_congestion.py (heatmap + analysis)
```

## Key Files

### Core Pipeline
- `main.py` - GME API data fetcher
- `src/gme_api/client.py` - GME API client
- `plotting/plotter.py` - Base visualization class

### Visualization Scripts
- `plot_gme.py` - Static price plots
- `plot_flows.py` - Static flow plots  
- `animate_flows.py` - Animated flow evolution
- `analyze_congestion.py` - Congestion analysis & heatmaps

### Network Data
- `data_pypsa_eur_zonal/` - PyPSA-Eur zonal network
- `italy_regions.geojson` - Italian regional boundaries

## Output Examples

All visualization outputs are saved to:
- `analysis/` - Congestion heatmaps and analysis plots
- `./*.gif` - Animated flow visualizations

**Note**: Output files are gitignored. See `cleanup1` branch for example outputs.

## Important Notes

### Capacity Sources
The pipeline uses **GME transmission limits** (not PyPSA s_nom estimates) for accurate utilization calculations:
- GME limits = real-time market constraints (40-60% of physical capacity)
- Accounts for N-1 security, voltage stability, real-time conditions

### Network Topology
- **Bidirectional corridors**: Some connections have asymmetric capacities
  - Example: NORD→CNOR = 10.5 GW, CNOR→NORD = 4.5 GW
- **External borders**: Connections to neighbors (AUST, SVIZ, FRAN, etc.)

## Requirements

- Python 3.10+
- PyPSA 0.35+
- Matplotlib, Cartopy, Seaborn
- GME API access credentials

## License

MIT
