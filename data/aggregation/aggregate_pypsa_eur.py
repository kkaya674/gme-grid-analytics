"""
PyPSA-Eur Network Aggregation to GME Zones
Filters Italy + neighbors from PyPSA-Eur, aggregates to GME market zones
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
PYPSA_DATA = PROJECT_ROOT / "pypsa_eur_data"
GEOJSON_PATH = PROJECT_ROOT / "aggregation" / "italy_regions.geojson"
OUTPUT_DIR = PROJECT_ROOT / "data_pypsa_eur_zonal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# GME zone mapping
REGION_TO_ZONE = {
    'Piemonte': 'NORD',
    "Valle d'Aosta/Vallée d'Aoste": 'NORD',
    'Lombardia': 'NORD',
    'Trentino-Alto Adige/Südtirol': 'NORD',
    'Veneto': 'NORD',
   'Friuli-Venezia Giulia': 'NORD',
    'Liguria': 'NORD',
    'Emilia-Romagna': 'NORD',
    'Toscana': 'CNOR',
    'Umbria': 'CNOR',
    'Marche': 'CNOR',
    'Lazio': 'CSUD',
    'Abruzzo': 'CSUD',
    'Molise': 'CSUD',
    'Campania': 'CSUD',
    'Puglia': 'SUD',
    'Basilicata': 'SUD',
    'Calabria': 'CALA',
    'Sicilia': 'SICI',
    'Sardegna': 'SARD'
}

COUNTRY_TO_ZONE = {
    'AT': 'AUST',
    'FR': 'FRAN',
    'CH': 'SVIZ',  # Switzerland in GME data
    'SI': 'SLOV',
    'GR': 'GREC',
    'ME': 'MONT'
}

def load_pypsa_eur():
    """Load PyPSA-Eur network CSVs."""
    print("=" * 60)
    print("LOADING PYPSA-EUR NETWORK")
    print("=" * 60)
    
    buses = pd.read_csv(PYPSA_DATA / 'buses.csv')
    
    # Load AC lines
    lines = pd.read_csv(
        PYPSA_DATA / 'lines.csv',
        usecols=['line_id', 'bus0', 'bus1', 'voltage', 'circuits', 'length'],
        quotechar="'",
        low_memory=False
    )
    
    # Load DC links (HVDC connections)
    links = pd.read_csv(
        PYPSA_DATA / 'links.csv',
        usecols=['link_id', 'bus0', 'bus1', 'voltage', 'p_nom', 'length'],
        quotechar="'",
        low_memory=False
    )
    
    print(f"   Total buses: {len(buses):,}")
    print(f"   Total AC lines: {len(lines):,}")
    print(f"   Total DC links: {len(links):,}")
    
    return buses, lines, links

def filter_italy_neighbors(buses, lines, links):
    """Filter only IT + neighbors."""
    print("\n" + "=" * 60)
    print("FILTERING ITALY + NEIGHBORS")
    print("=" * 60)
    
    target_countries = ['IT', 'AT', 'FR', 'CH', 'SI', 'GR', 'ME']
    buses_filtered = buses[buses.country.isin(target_countries)].copy()
    
    # Convert bus_id to int for matching with lines/links
    buses_filtered['bus_id'] = buses_filtered['bus_id'].astype(int)
    
    # Filter lines and links connecting these buses
    bus_ids = set(buses_filtered.bus_id)
    lines_filtered = lines[
        lines.bus0.isin(bus_ids) & lines.bus1.isin(bus_ids)
    ].copy()
    links_filtered = links[
        links.bus0.isin(bus_ids) & links.bus1.isin(bus_ids)
    ].copy()
    
    print(f"   Filtered buses: {len(buses_filtered):,}")
    print(f"   Filtered AC lines: {len(lines_filtered):,}")
    print(f"   Filtered DC links: {len(links_filtered):,}")
    for country in target_countries:
        count = len(buses_filtered[buses_filtered.country == country])
        print(f"      {country}: {count} buses")
    
    return buses_filtered, lines_filtered, links_filtered

def map_to_gme_zones(buses):
    """Map buses to GME zones."""
    print("\n" + "=" * 60)
    print("MAPPING TO GME ZONES")
    print("=" * 60)
    
    # Load Italian regions for spatial join
    regions = gpd.read_file(GEOJSON_PATH)
    
    buses['zone'] = None
    
    # Italian buses - spatial join
    it_mask = buses.country == 'IT'
    it_buses = buses[it_mask].copy()
    
    geometry = [Point(xy) for xy in zip(it_buses.x, it_buses.y)]
    it_gdf = gpd.GeoDataFrame(it_buses, geometry=geometry, crs="EPSG:4326")
    
    joined = gpd.sjoin(it_gdf, regions[['reg_name', 'geometry']], how='left', predicate='within')
    buses.loc[it_mask, 'zone'] = joined['reg_name'].map(REGION_TO_ZONE)
    
    # Fill NaN IT buses (coastal)
    nan_it = buses[it_mask & buses.zone.isna()]
    if not nan_it.empty:
        print(f"   Filling {len(nan_it)} coastal IT buses...")
        for idx, row in nan_it.iterrows():
            p = Point(row.x, row.y)
            dists = regions.distance(p)
            nearest_reg = regions.iloc[dists.idxmin()]['reg_name']
            buses.at[idx, 'zone'] = REGION_TO_ZONE.get(nearest_reg, 'NORD')
    
    # Neighbor buses
    neighbor_mask = buses.country.isin(COUNTRY_TO_ZONE.keys())
    buses.loc[neighbor_mask, 'zone'] = buses.loc[neighbor_mask, 'country'].map(COUNTRY_TO_ZONE)
    
    # Summary
    print(f"\n   Zone distribution:")
    for zone in sorted(buses.zone.unique()):
        if zone:
            count = len(buses[buses.zone == zone])
            print(f"      {zone}: {count} buses")
    
    return buses

def aggregate_to_zones(buses, lines, links):
    """Aggregate network to zonal level."""
    print("\n" + "=" * 60)
    print("AGGREGATING TO ZONES")
    print("=" * 60)
    
    # Zonal bus centers
    zonal_buses = buses.groupby('zone').agg({
        'x': 'mean',
        'y': 'mean',
        'bus_id': 'count',
        'voltage': 'max'
    }).reset_index()
    zonal_buses.columns = ['name', 'x', 'y', 'n_substations', 'max_voltage_kv']
    
    # Map original buses to zones
    bus_to_zone = buses.set_index('bus_id')['zone'].to_dict()
    
    # Aggregate AC lines
    lines['zone0'] = lines.bus0.map(bus_to_zone)
    lines['zone1'] = lines.bus1.map(bus_to_zone)
    inter_zonal_ac = lines[
        (lines.zone0.notna()) & 
        (lines.zone1.notna()) & 
        (lines.zone0 != lines.zone1)
    ].copy()
    
    zonal_ac = inter_zonal_ac.groupby(['zone0', 'zone1']).agg({
        'line_id': 'count',
        'voltage': 'max',
        'length': 'mean',
        'circuits': 'sum'
    }).reset_index()
    zonal_ac.columns = ['bus0', 'bus1', 'n_lines', 'voltage_kv', 'length_km', 'total_circuits']
    zonal_ac['type'] = 'AC'
    
    # Aggregate DC links
    links['zone0'] = links.bus0.map(bus_to_zone)
    links['zone1'] = links.bus1.map(bus_to_zone)
    inter_zonal_dc = links[
        (links.zone0.notna()) & 
        (links.zone1.notna()) & 
        (links.zone0 != links.zone1)
    ].copy()
    
    zonal_dc = inter_zonal_dc.groupby(['zone0', 'zone1']).agg({
        'link_id': 'count',
        'voltage': 'max',
        'length': 'mean',
        'p_nom': 'sum'  # DC links have p_nom directly
    }).reset_index()
    zonal_dc.columns = ['bus0', 'bus1', 'n_lines', 'voltage_kv', 'length_km', 'total_p_nom']
    zonal_dc['type'] = 'DC'
    
    # Combine AC and DC
    all_connections = []
    
    # Add AC lines
    for _, row in zonal_ac.iterrows():
        v = row['voltage_kv']
        n = max(row['total_circuits'], row['n_lines'])
        if v >= 380: s_nom = n * 1500
        elif v >= 220: s_nom = n * 500
        else: s_nom = n * 200
        
        all_connections.append({
            'bus0': row['bus0'],
            'bus1': row['bus1'],
            'n_lines': row['n_lines'],
            'voltage_kv': row['voltage_kv'],
            'length_km': row['length_km'],
            's_nom': s_nom,
            'type': 'AC'
        })
    
    # Add DC links
    for _, row in zonal_dc.iterrows():
        all_connections.append({
            'bus0': row['bus0'],
            'bus1': row['bus1'],
            'n_lines': row['n_lines'],
            'voltage_kv': row['voltage_kv'],
            'length_km': row['length_km'],
            's_nom': row['total_p_nom'],  # Use p_nom directly
            'type': 'DC'
        })
    
    zonal_lines = pd.DataFrame(all_connections)
    zonal_lines['name'] = zonal_lines.apply(lambda r: f"{r['bus0']}_{r['bus1']}", axis=1)
    zonal_lines['x'] = zonal_lines['length_km'] * 0.0001
    
    print(f"   Zonal buses: {len(zonal_buses)}")
    print(f"   Inter-zonal AC lines: {len(zonal_ac)}")
    print(f"   Inter-zonal DC links: {len(zonal_dc)}")
    print(f"   Total connections: {len(zonal_lines)}")
    
    return zonal_buses, zonal_lines

def save_results(zonal_buses, zonal_lines):
    """Save aggregated network."""
    zonal_buses_out = zonal_buses.copy().set_index('name')
    zonal_lines_out = zonal_lines.copy().set_index('name')
    
    zonal_buses_out.to_csv(OUTPUT_DIR / 'buses.csv')
    zonal_lines_out.to_csv(OUTPUT_DIR / 'lines.csv')
    
    print(f"\n   ✅ SAVED TO: {OUTPUT_DIR}")
    print(f"      Zones: {list(zonal_buses.name)}")

def main():
    buses, lines, links = load_pypsa_eur()
    buses_filt, lines_filt, links_filt = filter_italy_neighbors(buses, lines, links)
    buses_mapped = map_to_gme_zones(buses_filt)
    zonal_buses, zonal_lines = aggregate_to_zones(buses_mapped, lines_filt, links_filt)
    save_results(zonal_buses, zonal_lines)

if __name__ == "__main__":
    main()
