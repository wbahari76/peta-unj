import os
import math
import networkx as nx
import pandas as pd
from typing import Optional, Tuple, List
WALK_SPEED_M_PER_MIN = 83.3
OSM_GRAPH_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'unj_walknet.graphml')

def osm_network_available() -> bool:
    return os.path.exists(OSM_GRAPH_PATH)

def load_osm_network():
    if not osm_network_available():
        return None
    try:
        import osmnx as ox
    except ImportError:
        return None
    try:
        return ox.load_graphml(OSM_GRAPH_PATH)
    except Exception:
        return None

def _nearest_osm_node(G_osm, lat: float, lon: float) -> int:
    best_node, best_dist = (None, float('inf'))
    for node, data in G_osm.nodes(data=True):
        d = (data['y'] - lat) ** 2 + (data['x'] - lon) ** 2
        if d < best_dist:
            best_dist, best_node = (d, node)
    return best_node

def find_shortest_path_osm(G_osm, lat_asal: float, lon_asal: float, lat_tujuan: float, lon_tujuan: float) -> Tuple[Optional[List[Tuple[float, float]]], float]:
    n_asal = _nearest_osm_node(G_osm, lat_asal, lon_asal)
    n_tujuan = _nearest_osm_node(G_osm, lat_tujuan, lon_tujuan)
    if n_asal is None or n_tujuan is None or n_asal == n_tujuan:
        return (None, 0.0)
    try:
        path_nodes = nx.shortest_path(G_osm, n_asal, n_tujuan, weight='length')
        jarak = nx.shortest_path_length(G_osm, n_asal, n_tujuan, weight='length')
    except nx.NetworkXNoPath:
        return (None, 0.0)
    coords = [(lat_asal, lon_asal)]
    for a, b in zip(path_nodes[:-1], path_nodes[1:]):
        edge_data = G_osm.get_edge_data(a, b)
        best = min(edge_data.values(), key=lambda d: d.get('length', 0))
        geom = best.get('geometry')
        if geom is not None and hasattr(geom, 'coords'):
            seg = [(y, x) for x, y in geom.coords]
        else:
            na, nb = (G_osm.nodes[a], G_osm.nodes[b])
            seg = [(na['y'], na['x']), (nb['y'], nb['x'])]
        coords.extend(seg)
    coords.append((lat_tujuan, lon_tujuan))
    extra = _haversine(lat_asal, lon_asal, G_osm.nodes[n_asal]['y'], G_osm.nodes[n_asal]['x'])
    extra += _haversine(lat_tujuan, lon_tujuan, G_osm.nodes[n_tujuan]['y'], G_osm.nodes[n_tujuan]['x'])
    return (coords, round(jarak + extra, 1))

def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371000
    phi1, phi2 = (math.radians(lat1), math.radians(lat2))
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def build_graph(edges_df: pd.DataFrame, gedung_df: pd.DataFrame) -> nx.Graph:
    G = nx.Graph()
    for _, row in gedung_df.iterrows():
        G.add_node(int(row['id_gedung']), nama=row['nama_gedung'], lat=float(row['latitude']), lon=float(row['longitude']))
    for _, row in edges_df.iterrows():
        G.add_edge(int(row['id_asal']), int(row['id_tujuan']), weight=float(row['jarak_meter']))
    return G

def find_shortest_path(G: nx.Graph, id_asal: int, id_tujuan: int) -> Tuple[Optional[List[Tuple[float, float]]], Optional[List[int]], float]:
    if id_asal not in G or id_tujuan not in G:
        return (None, None, 0.0)
    if id_asal == id_tujuan:
        return (None, None, 0.0)
    try:
        path_nodes = nx.dijkstra_path(G, id_asal, id_tujuan, weight='weight')
        jarak = nx.dijkstra_path_length(G, id_asal, id_tujuan, weight='weight')
    except nx.NetworkXNoPath:
        return (None, None, 0.0)
    path_coords = [(G.nodes[n]['lat'], G.nodes[n]['lon']) for n in path_nodes]
    return (path_coords, path_nodes, round(jarak, 1))

def nearest_graph_node(G: nx.Graph, lat: float, lon: float) -> Optional[int]:
    best_node, best_dist = (None, float('inf'))
    for node, data in G.nodes(data=True):
        d = (data['lat'] - lat) ** 2 + (data['lon'] - lon) ** 2
        if d < best_dist:
            best_dist, best_node = (d, node)
    return best_node

def calculate_walking_time(distance_meters: float) -> float:
    return round(distance_meters / WALK_SPEED_M_PER_MIN, 1)