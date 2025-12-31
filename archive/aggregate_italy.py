"""
İTALYA ZONAL AGGREGATION

Substasyonları İtalya GME market zone'larına ve komşu ülkelere göre aggregate eder.
Zone'lar: NORD, CNOR, CSUD, SUD, CALA, SICI, SARD ve komşular (FRAN, CH12, AUST, SLOV, GREC, MONT).
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path
import os
import matplotlib.pyplot as plt

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data_italy"
GEOJSON_PATH = PROJECT_ROOT / "aggregation" / "italy_regions.geojson"
OUTPUT_DIR = DATA_DIR / "zonal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    """Veriyi yükle."""
    print("=" * 60)
    print("VERİ YÜKLENİYOR")
    print("=" * 60)
    
    substations = pd.read_csv(DATA_DIR / 'substations.csv')
    lines = pd.read_csv(DATA_DIR / 'lines_transmission.csv')
    generators = pd.read_csv(DATA_DIR / 'generators_with_capacity.csv')
    demand = pd.read_csv(DATA_DIR / 'demand_hourly.csv', index_col=0, parse_dates=True)
    
    print(f"   Substations: {len(substations):,}")
    print(f"   Transmission Lines: {len(lines):,}")
    print(f"   Generators (with capacity): {len(generators):,}")
    print(f"   Demand hours: {len(demand):,}")
    
    return substations, lines, generators, demand

def map_to_zones(substations):
    """Substasyonları GME zone'larına map et."""
    print("\n" + "=" * 60)
    print("ZONAL MAPPING")
    print("=" * 60)
    
    # Filter 132kV+
    hv_subs = substations[substations['voltage_kv'] >= 132].copy()
    hv_subs = hv_subs.dropna(subset=['lat', 'lon'])
    hv_subs = hv_subs[(hv_subs['lat'] != 0) & (hv_subs['lon'] != 0)]
    
    # Load geojson
    print(f"   Loading regions from {GEOJSON_PATH}")
    regions = gpd.read_file(GEOJSON_PATH)
    
    # Mapping table
    region_to_zone = {
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
    
    # Spatial join
    geometry = [Point(xy) for xy in zip(hv_subs.lon, hv_subs.lat)]
    subs_gdf = gpd.GeoDataFrame(hv_subs, geometry=geometry, crs="EPSG:4326")
    
    # Join with regions
    joined = gpd.sjoin(subs_gdf, regions[['reg_name', 'geometry']], how='left', predicate='within')
    hv_subs['zone'] = joined['reg_name'].map(region_to_zone)
    
    # Neighbors mapping (approximate based on coordinates for nodes outside Italy)
    neighbors = {
        'FRAN': (6.0, 45.0),
        'CH12': (8.5, 46.5),
        'AUST': (12.0, 47.0),
        'SLOV': (14.5, 46.0),
        'GREC': (20.0, 39.0),
        'MONT': (19.0, 42.5)
    }
    
    nan_subs = hv_subs[hv_subs['zone'].isna()].copy()
    if not nan_subs.empty:
        print(f"   Mapping {len(nan_subs)} nodes outside regions (coastal or neighbor)...")
        for idx, row in nan_subs.iterrows():
            # Check if it's a neighbor or just coastal Italy
            # Distance to nearest region
            p = Point(row.lon, row.lat)
            dists = regions.distance(p)
            min_dist = dists.min()
            
            if min_dist < 0.5: # Likely coastal Italy
                nearest_reg = regions.iloc[dists.idxmin()]['reg_name']
                hv_subs.at[idx, 'zone'] = region_to_zone.get(nearest_reg)
            else:
                # Map to nearest neighbor centroid
                best_n = 'NORD' # Default if nothing fits
                min_n_dist = float('inf')
                for n_name, (n_lon, n_lat) in neighbors.items():
                    d = np.sqrt((row.lon - n_lon)**2 + (row.lat - n_lat)**2)
                    if d < min_n_dist:
                        min_n_dist = d
                        best_n = n_name
                hv_subs.at[idx, 'zone'] = best_n
    
    # Aggregate zonal centroids
    zonal_centers = hv_subs.groupby('zone').agg({
        'lat': 'mean',
        'lon': 'mean',
        'osm_id': 'count',
        'voltage_kv': 'max'
    }).reset_index()
    zonal_centers.columns = ['bus_id', 'lat', 'lon', 'n_substations', 'max_voltage_kv']
    
    print(f"   Mapping complete. Found {len(hv_subs['zone'].unique())} zones.")
    for zone in sorted(hv_subs['zone'].unique()):
        count = len(hv_subs[hv_subs.zone == zone])
        print(f"      {zone}: {count} substations")
        
    return hv_subs, zonal_centers

def aggregate_lines(lines, hv_subs, centers):
    """Hatları zonalara aggregate et."""
    print("\n" + "=" * 60)
    print("HAT AGGREGATION")
    print("=" * 60)
    
    # Map start/end to zones
    # Use spatial joining logic or nearest node mapping if available
    # Since we have hv_subs with zone, let's match line endpoints to nearest hv_sub
    
    def find_zone(lat, lon):
        dists = np.sqrt((hv_subs['lat'] - lat)**2 + (hv_subs['lon'] - lon)**2)
        return hv_subs.loc[dists.idxmin()]['zone']
    
    lines = lines.copy()
    print("   Mapping line endpoints to zones...")
    lines['zone_start'] = lines.apply(lambda r: find_zone(r['lat_start'], r['lon_start']), axis=1)
    lines['zone_end'] = lines.apply(lambda r: find_zone(r['lat_end'], r['lon_end']), axis=1)
    
    inter_zonal = lines[lines['zone_start'] != lines['zone_end']].copy()
    
    agg_lines = inter_zonal.groupby(['zone_start', 'zone_end']).agg({
        'osm_id': 'count',
        'voltage_kv': 'max',
        'length_km': 'mean',
        'circuits': lambda x: x.astype(str).str.extract('(\d+)').astype(float).sum().fillna(1),
    }).reset_index()
    
    agg_lines.columns = ['bus0', 'bus1', 'n_lines', 'voltage_kv', 'length_km', 'total_circuits']
    agg_lines['line_id'] = agg_lines.apply(lambda r: f"{r['bus0']}_{r['bus1']}", axis=1)
    
    def estimate_capacity(row):
        v = row['voltage_kv']
        n = max(row['total_circuits'], row['n_lines'])
        if v >= 380: return n * 1500
        elif v >= 220: return n * 500
        else: return n * 200
        
    agg_lines['s_nom'] = agg_lines.apply(estimate_capacity, axis=1)
    agg_lines['x'] = agg_lines['length_km'] * 0.0001
    
    print(f"   Aggregated inter-zonal lines: {len(agg_lines)}")
    return agg_lines

def aggregate_generators(generators, hv_subs, centers):
    """Jeneratörleri zonalara aggregate et."""
    print("\n" + "=" * 60)
    print("JENERATÖR AGGREGATION")
    print("=" * 60)
    
    generators = generators.copy()
    
    def find_zone(lat, lon):
        if pd.isna(lat) or pd.isna(lon): return 'NORD'
        dists = np.sqrt((hv_subs['lat'] - lat)**2 + (hv_subs['lon'] - lon)**2)
        return hv_subs.loc[dists.idxmin()]['zone']
    
    print("   Mapping generators to zones...")
    generators['bus'] = generators.apply(lambda r: find_zone(r['lat'], r['lon']), axis=1)
    
    agg_gens = generators.groupby(['bus', 'carrier']).agg({
        'capacity_mw': 'sum',
        'osm_id': 'count'
    }).reset_index()
    
    agg_gens.columns = ['bus', 'carrier', 'p_nom', 'n_units']
    agg_gens['gen_id'] = agg_gens.apply(lambda r: f"{r['bus']}_{r['carrier']}", axis=1)
    
    mc_map = {'CCGT': 65, 'coal': 45, 'oil': 120, 'hydro': 5, 'solar': 0, 'wind': 0, 'biomass': 80, 'biogas': 75, 'geothermal': 10, 'waste': 50, 'other': 90}
    agg_gens['marginal_cost'] = agg_gens['carrier'].map(mc_map).fillna(100)
    
    return agg_gens

def distribute_load(demand, centers, substations):
    """Talebi zonalara dağıt."""
    # Simplified: use substation count as weight per zone
    weights = centers.set_index('bus_id')['n_substations']
    weights = weights / weights.sum()
    
    load_profiles = {}
    for zone in centers['bus_id']:
        load_profiles[zone] = demand['demand_mw'].values * weights[zone]
        
    load_df = pd.DataFrame(load_profiles, index=demand.index)
    return load_df, weights

def save_results(centers, agg_lines, agg_gens, load_df):
    """Sonuçları kaydet."""
    # Rename for PyPSA compatibility
    centers = centers.rename(columns={'lon': 'x', 'lat': 'y', 'bus_id': 'name'}).set_index('name')
    agg_lines = agg_lines.rename(columns={'line_id': 'name'}).set_index('name')
    agg_gens = agg_gens.rename(columns={'gen_id': 'name'}).set_index('name')
    
    centers.to_csv(OUTPUT_DIR / 'buses.csv')
    agg_lines.to_csv(OUTPUT_DIR / 'lines.csv')
    agg_gens.to_csv(OUTPUT_DIR / 'generators.csv')
    load_df.to_csv(OUTPUT_DIR / 'load_profiles.csv')
    
    summary = {
        'n_buses': len(centers),
        'n_lines': len(agg_lines),
        'total_gen_capacity_mw': agg_gens['p_nom'].sum(),
        'peak_demand_mw': load_df.sum(axis=1).max(),
    }
    pd.DataFrame([summary]).to_csv(OUTPUT_DIR / 'zonal_summary.csv', index=False)
    print(f"\n   ✅ ZONAL AGGREGATION TAMAMLANDI")
    print(f"   📁 Veriler: {OUTPUT_DIR}")

def main():
    substations, lines, generators, demand = load_data()
    hv_subs, centers = map_to_zones(substations)
    agg_lines = aggregate_lines(lines, hv_subs, centers)
    agg_gens = aggregate_generators(generators, hv_subs, centers)
    load_df, weights = distribute_load(demand, centers, substations)
    save_results(centers, agg_lines, agg_gens, load_df)

if __name__ == "__main__":
    main()
