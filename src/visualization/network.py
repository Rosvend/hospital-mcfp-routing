import osmnx as ox 
import networkx as nx 
import pickle 
import random
import numpy as np
from pathlib import Path


class NetworkManager:
    """Handles road network extraction and management"""

    def __init__(self, cache_dir="data/"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.graph = None
        self.center_point = None
        
    def load_network(self, center_point, method='circle', distance=560, use_cache=True):
        """
        Load road network from OSMnx
        Parameters:
        - center_point: (lat, lon) tuple
        - method: 'circle' or 'square'
        - distance: radius in meters (for circle) or half-side length (for square)
        - use_cache: whether to use cached network
        """
        cache_file = self.cache_dir / f"network_{center_point[0]}_{center_point[1]}_{method}_{distance}.pkl"
        
        # Try to load from cache if requested
        if use_cache and cache_file.exists():
            print(f"Loading cached network from {cache_file}")
            return self.load_cached_network(cache_file)
        
        # Download network from OSM
        print(f"Downloading network from OpenStreetMap...")
        
        try:
            if method == 'circle':
                # Create network from point with radius
                self.graph = ox.graph_from_point(
                    center_point, 
                    dist=distance, 
                    network_type='drive',
                    simplify=True
                )
            else:  # square
                # Create bounding box
                north = ox.distance.great_circle(center_point[0], center_point[1], 
                                                 center_point[0] + distance/111000, center_point[1])
                south = ox.distance.great_circle(center_point[0], center_point[1], 
                                                 center_point[0] - distance/111000, center_point[1])
                east = ox.distance.great_circle(center_point[0], center_point[1], 
                                                center_point[0], center_point[1] + distance/(111000 * np.cos(np.radians(center_point[0]))))
                west = ox.distance.great_circle(center_point[0], center_point[1], 
                                                center_point[0], center_point[1] - distance/(111000 * np.cos(np.radians(center_point[0]))))
                
                self.graph = ox.graph_from_point(
                    center_point, 
                    dist=distance, 
                    network_type='drive',
                    simplify=True
                )
            
            self.center_point = center_point
            
            # Add travel time attributes
            self.graph = ox.add_edge_speeds(self.graph)
            self.graph = ox.add_edge_travel_times(self.graph)
            
            # Convert to strongly connected graph (so all nodes are reachable)
            if not nx.is_strongly_connected(self.graph):
                largest_scc = max(nx.strongly_connected_components(self.graph), key=len)
                self.graph = self.graph.subgraph(largest_scc).copy()
            
            # Save to cache
            if use_cache:
                self.save_network(cache_file)
            
            print(f"Network loaded: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")
            return self.graph
            
        except Exception as e:
            print(f"Error loading network: {e}")
            raise
    
    def assign_random_capacities(self, c_min=20, c_max=80):
        """Assign random speed capacities to edges"""
        if self.graph is None:
            raise ValueError("No network loaded. Call load_network() first.")
        
        for u, v, key in self.graph.edges(keys=True):
            # Assign random capacity (speed limit in km/h)
            capacity = random.uniform(c_min, c_max)
            self.graph.edges[u, v, key]['capacity'] = capacity
        
        print(f"Assigned random capacities between {c_min} and {c_max} km/h")
        return self.graph
    
    def get_random_nodes(self, origin_node=None, n_destinations=3):
        """
        Select random destination nodes reachable from origin
        Returns: (origin_node, list_of_destination_nodes)
        """
        if self.graph is None:
            raise ValueError("No network loaded. Call load_network() first.")
        
        nodes = list(self.graph.nodes())
        
        # If no origin specified, pick random origin
        if origin_node is None:
            origin_node = random.choice(nodes)
        
        # Find nodes that are reachable from origin
        reachable = nx.descendants(self.graph, origin_node)
        reachable.add(origin_node)  # Include origin itself
        reachable_list = list(reachable)
        
        if len(reachable_list) < n_destinations + 1:
            print(f"Warning: Only {len(reachable_list)} reachable nodes, requested {n_destinations} destinations")
            n_destinations = max(1, len(reachable_list) - 1)
        
        # Remove origin from reachable list
        if origin_node in reachable_list:
            reachable_list.remove(origin_node)
        
        # Select random destinations
        destinations = random.sample(reachable_list, min(n_destinations, len(reachable_list)))
        
        return origin_node, destinations
    
    def get_node_coordinates(self, node):
        """Get lat, lon coordinates for a node"""
        if self.graph is None:
            raise ValueError("No network loaded.")
        return (self.graph.nodes[node]['y'], self.graph.nodes[node]['x'])
    
    def save_network(self, filename):
        """Cache network to disk"""
        if self.graph is None:
            raise ValueError("No network to save.")
        
        with open(filename, 'wb') as f:
            pickle.dump({
                'graph': self.graph,
                'center_point': self.center_point
            }, f)
        print(f"Network saved to {filename}")
    
    def load_cached_network(self, filename):
        """Load cached network"""
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            self.graph = data['graph']
            self.center_point = data.get('center_point')
        print(f"Network loaded from cache: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")
        return self.graph
    
    def plot_network(self):
        """Plot network using OSMnx"""
        if self.graph is None:
            raise ValueError("No network loaded.")
        
        fig, ax = ox.plot_graph(self.graph, node_size=10, edge_linewidth=0.5, 
                               show=False, close=False)
        return fig

