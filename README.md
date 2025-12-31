# GME Market Visualization & Analysis Pipeline

> [!IMPORTANT]
> **Information**: This is a personal development project. It has no official affiliation with GME (Gestore dei Mercati Energetici).

Python pipeline for analyzing Italian electricity markets (GME) with PyPSA-Eur network topology.

## Features

- 🔌 **Network Visualization**: PyPSA-Eur zonal network with Italian market zones
- 📊 **Price Mapping**: MGP, MSD, MB market prices on network topology  
- 🌊 **Flow Analysis**: Transmission flows with GME market limits
- 📈 **Congestion Analysis**: 96-session heatmaps (15-min granularity)
- ⚖️ **Balancing Markets**: MSD and MB (RS/AS) price and volume analysis
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

### 2. Docker Setup (Alternative)

If you prefer using Docker, you can run the pipeline without installing local dependencies:

```bash
# Build the image
docker compose build

# Fetch data for a specific date
docker compose run app python src/main.py --date 2025-12-30

# Run congestion analysis
docker compose run app python src/analyze_congestion.py --date 2025-12-30
```

### 3. VS Code Dev Containers

This project is configured for [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers). 
1. Open the project in VS Code.
2. Click **"Reopen in Container"** when prompted, or use the Command Palette (`Ctrl+Shift+P`) and select `Dev Containers: Reopen in Container`.
3. The environment will be automatically set up with all dependencies and recommended extensions.

### 4. Configure GME Credentials

Create `.env` file with your GME API credentials:

```
GME_USERNAME=your_username
GME_PASSWORD=your_password
```

### 3. Fetch Market Data

```bash
# Fetch data for yesterday (default)
python src/main.py

# Or fetch for a specific date
python src/main.py --date 2025-12-30


```

### 4. Generate Visualizations

```bash
# === CONGESTION ANALYSIS ===
python src/analyze_congestion.py --date 2025-12-30
# Outputs to workspace/:
# - congestion_heatmap_96sessions.png (>5% avg utilization corridors)
# - corridor_timeseries.png
# - morning_vs_midday.png

# === BALANCING MARKETS ===
python src/analyze_balancing.py --date 2025-12-30
# Outputs (9 total) to workspace/:
# MSD: zone price comparison, buy/sell volumes
# MB_RS: zone price comparison, buy/sell volumes  
# MB_AS: zone price comparison, buy/sell volumes

# === FLOW ANIMATION ===
python src/animate_flows.py --date 2025-12-30 --output workspace/mgp_animation.gif
# 96-frame animated GIF showing 24h flow evolution

# === STATIC PLOTS ===
python src/plot_gme.py --market MGP --hour 12 --date 2025-12-30
python src/plot_flows.py --date 2025-12-30 --hour 12
```

## Repository Structure

```
gme_api/
├── src/                         # All source code
│   ├── gme_api/                 # Core API library
│   │   ├── client.py            # GME API client
│   │   └── utils.py             # Data processing utilities
│   ├── plotting/                # Visualization library
│   │   ├── plotter.py           # Base plotter class
│   │   └── utils.py             # Plot utilities
│   ├── main.py                  # Data fetcher
│   ├── analyze_congestion.py    # Congestion analysis
│   ├── analyze_balancing.py     # Balancing markets analysis
│   ├── animate_flows.py         # Flow animation
│   ├── plot_gme.py              # Static price plots
│   └── plot_flows.py            # Static flow plots
│
├── data/                        # Static data
│   ├── network/                 # Network topology data
│   └── aggregation/             # Aggregation scripts & data
│
├── workspace/                   # Generated outputs (gitignored)
│   ├── *.csv                    # Market data CSVs
│   ├── *.png                    # Analysis visualizations
│   └── *.gif                    # Animations
│
├── documents/                   # Documentation & PDFs
├── archive/                     # Archived code
├── .devcontainer/               # Dev container configuration
└── requirements.txt             # Dependencies
```

## Key Analysis Scripts

### 1. Congestion Analysis (`analyze_congestion.py`)
- **96-session heatmap**: Shows utilization across all 15-min intervals
- **Filters**: Only corridors with >5% avg utilization
- **Key findings**: CSUD→SUD (72% peak), CSUD→SARD (70% peak)

### 2. Balancing Analysis (`analyze_balancing.py`)
Analyzes three markets:
- **MSD**: Mercato del Servizio di Dispacciamento (ex-ante)
- **MB_RS**: Riserva Secondaria (secondary reserve)
- **MB_AS**: Altro Servizi (other services)

Each market generates:
- Zone-specific price comparison (vs MGP)
- Buy volume bar charts (7 zones)
- Sell volume bar charts (7 zones)

### 3. Flow Animation (`animate_flows.py`)
- 96 frames (24 hours × 4 periods)
- Dynamic price updates per zone
- Flow utilization coloring (0-100%)
- Zone labels and country borders

## Important Notes

### Capacity Sources
The pipeline uses **GME transmission limits** (not PyPSA s_nom) for accurate utilization:
- GME limits = real-time market constraints (40-60% of physical capacity)
- Accounts for N-1 security, voltage stability, real-time conditions

### Network Topology
- **Bidirectional corridors**: Asymmetric capacities
  - Example: NORD→CNOR = 10.5 GW, CNOR→NORD = 4.5 GW
- **Italian zones**: NORD, CNOR, CSUD, SUD, CALA, SICI, SARD
- **External borders**: AUST, SVIZ, FRAN, SLOV, GREC, MONT

### Balancing Markets
- **MSD**: Day-ahead balancing (ex-ante)
  - Mostly upward regulation (grid shortage)
- **MB_RS**: Real-time secondary reserve
  - Often zero activity
- **MB_AS**: Real-time other services
  - Most active balancing market

## Output Examples

All visualizations saved to `analysis/`:
- Congestion heatmaps (PNG)
- Balancing price/volume charts (PNG)
- Flow animations (GIF)

**Note**: Output files are gitignored. See `cleanup1` branch for example outputs.

## Requirements

- Python 3.10+
- PyPSA 0.35+
- Matplotlib, Cartopy, Seaborn
- GME API access credentials

## License

MIT

---

> [!CAUTION]
> ### Disclaimer
> This software is provided "as is" for educational and analytical purposes. The authors cannot be held responsible for the accuracy or timeliness of the data, or for any consequences arising from commercial or operational decisions made using this tool. Users are responsible for complying with GME's data usage terms and conditions.
