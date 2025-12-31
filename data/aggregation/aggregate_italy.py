"""
İTALYA 30-NODE AGGREGATION

132kV ve üzeri substasyonları K-means ile 30 bölgeye cluster'lar.
Her cluster için:
- Buses: Cluster merkezi
- Lines: Clusterlar arası bağlantılar
- Generators: Cluster'a en yakın santraller
- Loads: Talep orantılı dağılım
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data_italy"
OUTPUT_DIR = PROJECT_ROOT / "data_italy" / "aggregated_30"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_CLUSTERS = 30


def load_data():
    """Veriyi yükle."""
    print("=" * 60)
    print("VERİ YÜKLENİYOR")
    print("=" * 60)
    
    substations = pd.read_csv(DATA_DIR / 'substations.csv')
    lines = pd.read_csv(DATA_DIR / 'lines_transmission.csv')  # >=132kV
    generators = pd.read_csv(DATA_DIR / 'generators_with_capacity.csv')
    demand = pd.read_csv(DATA_DIR / 'demand_hourly.csv', index_col=0, parse_dates=True)
    
    print(f"   Substations: {len(substations):,}")
    print(f"   Transmission Lines: {len(lines):,}")
    print(f"   Generators (with capacity): {len(generators):,}")
    print(f"   Demand hours: {len(demand):,}")
    
    return substations, lines, generators, demand


def cluster_substations(substations, n_clusters=N_CLUSTERS):
    """132kV+ substasyonları cluster'la."""
    print("\n" + "=" * 60)
    print(f"CLUSTERING: {n_clusters} NODE")
    print("=" * 60)
    
    # Filter 132kV+
    hv_subs = substations[substations['voltage_kv'] >= 132].copy()
    print(f"   132kV+ substasyonlar: {len(hv_subs):,}")
    
    # Remove invalid coordinates
    hv_subs = hv_subs[(hv_subs['lat'] != 0) & (hv_subs['lon'] != 0)].copy()
    hv_subs = hv_subs.dropna(subset=['lat', 'lon'])
    print(f"   Valid koordinatlı: {len(hv_subs):,}")
    
    # K-means clustering
    coords = hv_subs[['lat', 'lon']].values
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    hv_subs['cluster'] = kmeans.fit_predict(coords)
    
    # Cluster centers
    centers = pd.DataFrame({
        'bus_id': [f'IT_{i:02d}' for i in range(n_clusters)],
        'lat': kmeans.cluster_centers_[:, 0],
        'lon': kmeans.cluster_centers_[:, 1],
    })
    
    # Add cluster statistics
    cluster_stats = hv_subs.groupby('cluster').agg({
        'osm_id': 'count',
        'voltage_kv': 'max',
        'name': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else ''
    }).reset_index()
    cluster_stats.columns = ['cluster', 'n_substations', 'max_voltage_kv', 'sample_name']
    
    centers = centers.merge(cluster_stats, left_index=True, right_on='cluster')
    centers = centers.drop('cluster', axis=1)
    
    # İtalya bölgelerine göre isimlendir (yaklaşık)
    region_names = assign_region_names(centers)
    centers['region'] = region_names
    
    print(f"\n   Cluster dağılımı:")
    for _, row in centers.iterrows():
        print(f"      {row['bus_id']}: {row['n_substations']} subs, {row['max_voltage_kv']:.0f}kV, ~{row['region']}")
    
    return hv_subs, centers


def assign_region_names(centers):
    """Koordinatlara göre bölge isimleri ata."""
    # İtalya bölgeleri (yaklaşık koordinatlar)
    regions = [
        ('Sicilia', 37.5, 14.0),
        ('Calabria', 38.9, 16.3),
        ('Puglia', 41.0, 17.0),
        ('Basilicata', 40.5, 16.0),
        ('Campania', 40.8, 14.8),
        ('Sardegna', 40.0, 9.0),
        ('Lazio', 41.9, 12.5),
        ('Abruzzo', 42.3, 13.8),
        ('Molise', 41.7, 14.7),
        ('Marche', 43.3, 13.5),
        ('Umbria', 42.8, 12.6),
        ('Toscana', 43.3, 11.2),
        ('Emilia-Romagna', 44.5, 11.3),
        ('Liguria', 44.3, 8.9),
        ('Piemonte', 45.0, 7.7),
        ('Valle d\'Aosta', 45.7, 7.3),
        ('Lombardia', 45.5, 9.5),
        ('Trentino', 46.1, 11.1),
        ('Veneto', 45.5, 11.8),
        ('Friuli', 46.0, 13.2),
    ]
    
    region_names = []
    for _, row in centers.iterrows():
        min_dist = float('inf')
        nearest = 'Italia'
        for name, lat, lon in regions:
            dist = np.sqrt((row['lat'] - lat)**2 + (row['lon'] - lon)**2)
            if dist < min_dist:
                min_dist = dist
                nearest = name
        region_names.append(nearest)
    
    return region_names


def aggregate_lines(lines, hv_subs, centers):
    """Hatları cluster'lar arası bağlantılara aggregate et."""
    print("\n" + "=" * 60)
    print("HAT AGGREGATION")
    print("=" * 60)
    
    # Her line'ın start/end noktasını en yakın cluster'a ata
    def find_nearest_cluster(lat, lon, centers):
        dists = np.sqrt((centers['lat'] - lat)**2 + (centers['lon'] - lon)**2)
        return dists.idxmin()
    
    lines = lines.copy()
    lines['cluster_start'] = lines.apply(
        lambda r: find_nearest_cluster(r['lat_start'], r['lon_start'], centers), axis=1
    )
    lines['cluster_end'] = lines.apply(
        lambda r: find_nearest_cluster(r['lat_end'], r['lon_end'], centers), axis=1
    )
    
    # Cluster'lar arası bağlantıları aggregate et
    inter_cluster = lines[lines['cluster_start'] != lines['cluster_end']].copy()
    
    # Her cluster çifti için toplam kapasite
    agg_lines = inter_cluster.groupby(['cluster_start', 'cluster_end']).agg({
        'osm_id': 'count',
        'voltage_kv': 'max',
        'length_km': 'mean',
        'circuits': lambda x: x.astype(str).str.extract('(\d+)').astype(float).sum(),
    }).reset_index()
    
    agg_lines.columns = ['bus0_idx', 'bus1_idx', 'n_lines', 'voltage_kv', 'length_km', 'total_circuits']
    
    # Bus ID'leri ekle
    agg_lines['bus0'] = agg_lines['bus0_idx'].apply(lambda i: centers.iloc[i]['bus_id'])
    agg_lines['bus1'] = agg_lines['bus1_idx'].apply(lambda i: centers.iloc[i]['bus_id'])
    agg_lines['line_id'] = agg_lines.apply(lambda r: f"{r['bus0']}_{r['bus1']}", axis=1)
    
    # Kapasite tahmini: voltage * circuits * 1.5 (yaklaşık thermal limit)
    # 380kV double circuit ~ 2000 MW, 220kV ~ 500 MW, 132kV ~ 200 MW
    def estimate_capacity(row):
        v = row['voltage_kv']
        n = max(row['total_circuits'], row['n_lines'])
        if v >= 380:
            return n * 1500  # MW per circuit
        elif v >= 220:
            return n * 500
        else:
            return n * 200
    
    agg_lines['s_nom'] = agg_lines.apply(estimate_capacity, axis=1)
    
    # X (reactance) tahmini: length-based
    agg_lines['x'] = agg_lines['length_km'] * 0.0001  # pu/km yaklaşık
    
    print(f"   Toplam inter-cluster hat: {len(inter_cluster):,}")
    print(f"   Aggregated bağlantı: {len(agg_lines)}")
    print(f"   Toplam transfer kapasitesi: {agg_lines['s_nom'].sum():,.0f} MW")
    
    return agg_lines[['line_id', 'bus0', 'bus1', 'voltage_kv', 'length_km', 's_nom', 'x', 'n_lines']]


def aggregate_generators(generators, centers):
    """Jeneratörleri en yakın cluster'a ata."""
    print("\n" + "=" * 60)
    print("JENERATÖR AGGREGATION")
    print("=" * 60)
    
    generators = generators.copy()
    
    # Her jeneratörü en yakın cluster'a ata
    def find_nearest_cluster(lat, lon, centers):
        if pd.isna(lat) or pd.isna(lon):
            return 0
        dists = np.sqrt((centers['lat'] - lat)**2 + (centers['lon'] - lon)**2)
        return dists.idxmin()
    
    generators['cluster'] = generators.apply(
        lambda r: find_nearest_cluster(r['lat'], r['lon'], centers), axis=1
    )
    generators['bus'] = generators['cluster'].apply(lambda i: centers.iloc[i]['bus_id'])
    
    # Carrier bazında aggregate
    agg_gens = generators.groupby(['bus', 'carrier']).agg({
        'capacity_mw': 'sum',
        'osm_id': 'count',
        'name': lambda x: x.iloc[0] if len(x) > 0 else ''
    }).reset_index()
    
    agg_gens.columns = ['bus', 'carrier', 'p_nom', 'n_units', 'sample_name']
    agg_gens['gen_id'] = agg_gens.apply(lambda r: f"{r['bus']}_{r['carrier']}", axis=1)
    
    # Marginal cost (EUR/MWh)
    mc_map = {
        'CCGT': 65,
        'coal': 45,
        'oil': 120,
        'hydro': 5,
        'solar': 0,
        'wind': 0,
        'biomass': 80,
        'biogas': 75,
        'geothermal': 10,
        'waste': 50,
        'other': 90,
    }
    agg_gens['marginal_cost'] = agg_gens['carrier'].map(mc_map).fillna(100)
    
    print(f"\n   Carrier bazında toplam kapasite:")
    for carrier in agg_gens['carrier'].unique():
        total = agg_gens[agg_gens['carrier'] == carrier]['p_nom'].sum()
        print(f"      {carrier}: {total:,.0f} MW")
    
    return agg_gens[['gen_id', 'bus', 'carrier', 'p_nom', 'marginal_cost', 'n_units']]


def distribute_load(demand, centers):
    """Talebi bus'lara dağıt."""
    print("\n" + "=" * 60)
    print("TALEP DAĞILIMI")
    print("=" * 60)
    
    # Nüfus/endüstri yoğunluğuna göre (yaklaşık)
    # Kuzey İtalya daha fazla tüketir
    weights = []
    for _, row in centers.iterrows():
        lat = row['lat']
        if lat > 45:  # Kuzey
            w = 1.5
        elif lat > 43:  # Orta
            w = 1.2
        elif lat > 41:  # Orta-Güney
            w = 1.0
        else:  # Güney + adalar
            w = 0.8
        
        # Substasyon sayısı ile de ağırlıklandır
        w *= row['n_substations']
        weights.append(w)
    
    weights = np.array(weights)
    weights = weights / weights.sum()
    
    # Her bus için yük profili
    load_profiles = {}
    for i, (_, row) in enumerate(centers.iterrows()):
        bus_id = row['bus_id']
        load_profiles[bus_id] = demand['demand_mw'].values * weights[i]
    
    load_df = pd.DataFrame(load_profiles, index=demand.index)
    
    print(f"   Peak talep dağılımı:")
    for bus_id in load_df.columns[:5]:
        print(f"      {bus_id}: {load_df[bus_id].max():,.0f} MW peak")
    print(f"      ...")
    
    return load_df, weights


def save_results(centers, agg_lines, agg_gens, load_df, weights):
    """Sonuçları kaydet."""
    print("\n" + "=" * 60)
    print("SONUÇLAR KAYDEDİLİYOR")
    print("=" * 60)
    
    # Buses
    buses = centers[['bus_id', 'lat', 'lon', 'region', 'n_substations', 'max_voltage_kv']].copy()
    buses['load_weight'] = weights
    buses.to_csv(OUTPUT_DIR / 'buses.csv', index=False)
    print(f"   ✓ buses.csv ({len(buses)} buses)")
    
    # Lines
    agg_lines.to_csv(OUTPUT_DIR / 'lines.csv', index=False)
    print(f"   ✓ lines.csv ({len(agg_lines)} lines)")
    
    # Generators
    agg_gens.to_csv(OUTPUT_DIR / 'generators.csv', index=False)
    print(f"   ✓ generators.csv ({len(agg_gens)} generators)")
    
    # Load profiles (full year hourly)
    load_df.to_csv(OUTPUT_DIR / 'load_profiles.csv')
    print(f"   ✓ load_profiles.csv ({len(load_df)} hours x {len(load_df.columns)} buses)")
    
    # Summary
    summary = {
        'n_buses': len(buses),
        'n_lines': len(agg_lines),
        'n_generators': len(agg_gens),
        'total_gen_capacity_mw': agg_gens['p_nom'].sum(),
        'total_line_capacity_mw': agg_lines['s_nom'].sum(),
        'peak_demand_mw': load_df.sum(axis=1).max(),
    }
    pd.DataFrame([summary]).to_csv(OUTPUT_DIR / 'summary.csv', index=False)
    
    print(f"\n   📊 ÖZET:")
    print(f"      Buses: {summary['n_buses']}")
    print(f"      Lines: {summary['n_lines']}")
    print(f"      Generators: {summary['n_generators']}")
    print(f"      Total Gen Capacity: {summary['total_gen_capacity_mw']:,.0f} MW")
    print(f"      Total Line Capacity: {summary['total_line_capacity_mw']:,.0f} MW")
    print(f"      Peak Demand: {summary['peak_demand_mw']:,.0f} MW")
    
    return buses


def plot_italy_grid(buses, agg_lines):
    """İtalya grid haritasını çiz."""
    print("\n" + "=" * 60)
    print("HARİTA ÇİZİLİYOR")
    print("=" * 60)
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 14))
    
    # İtalya sınırları (yaklaşık)
    ax.set_xlim(6, 19)
    ax.set_ylim(35.5, 47.5)
    
    # Hatları çiz
    for _, line in agg_lines.iterrows():
        bus0 = buses[buses['bus_id'] == line['bus0']].iloc[0]
        bus1 = buses[buses['bus_id'] == line['bus1']].iloc[0]
        
        # Hat kalınlığı kapasiteye göre
        lw = max(0.5, min(3, line['s_nom'] / 5000))
        alpha = 0.4
        
        ax.plot([bus0['lon'], bus1['lon']], 
                [bus0['lat'], bus1['lat']], 
                'b-', linewidth=lw, alpha=alpha, zorder=1)
    
    # Bus'ları çiz
    sizes = buses['n_substations'] * 3  # Boyut substasyon sayısına göre
    scatter = ax.scatter(buses['lon'], buses['lat'], 
                         s=sizes, c='red', edgecolors='darkred', 
                         linewidths=1.5, zorder=2, alpha=0.8)
    
    # İsimleri yaz
    for _, bus in buses.iterrows():
        # Offset hesapla (çakışmayı önlemek için)
        offset_x = 0.15
        offset_y = 0.1
        
        # Bus ID ve bölge
        label = f"{bus['bus_id']}\n({bus['region']})"
        
        ax.annotate(label, 
                    xy=(bus['lon'], bus['lat']),
                    xytext=(bus['lon'] + offset_x, bus['lat'] + offset_y),
                    fontsize=7,
                    ha='left',
                    va='bottom',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='gray'),
                    zorder=3)
    
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.set_title('İtalya 30-Node Aggregated Grid\n(132kV+ Substasyonlar)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    # Legend
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', 
                   markersize=10, label='Bus (Aggregated Node)'),
        plt.Line2D([0], [0], color='blue', linewidth=2, alpha=0.5, 
                   label='Transmission Line'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)
    
    plt.tight_layout()
    
    # Kaydet
    plot_path = OUTPUT_DIR / 'italy_30_node_map.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"   ✓ Harita kaydedildi: {plot_path}")
    
    plt.show()
    
    return fig


def main():
    print("\n" + "=" * 70)
    print("   İTALYA 30-NODE AGGREGATION")
    print("=" * 70)
    
    # 1. Load data
    substations, lines, generators, demand = load_data()
    
    # 2. Cluster substations
    hv_subs, centers = cluster_substations(substations)
    
    # 3. Aggregate lines
    agg_lines = aggregate_lines(lines, hv_subs, centers)
    
    # 4. Aggregate generators
    agg_gens = aggregate_generators(generators, centers)
    
    # 5. Distribute load
    load_df, weights = distribute_load(demand, centers)
    
    # 6. Save results
    buses = save_results(centers, agg_lines, agg_gens, load_df, weights)
    
    # 7. Plot map
    plot_italy_grid(buses, agg_lines)
    
    print("\n" + "=" * 70)
    print("   ✅ TAMAMLANDI")
    print(f"   📁 Aggregated data: {OUTPUT_DIR}")
    print("=" * 70)
    print("=" * 70)


if __name__ == "__main__":
    main()
