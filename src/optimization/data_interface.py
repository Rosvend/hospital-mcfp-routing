# src/optimization/data_interface.py

class OptimizationData:
    """Data structure to pass network data to optimization model"""
    
    def __init__(self):
        self.nodes = []  # List of node IDs
        self.edges = []  # List of (u, v, key) tuples
        self.edge_data = {}  # {(u,v,key): {'length', 'capacity', 'time'}}
        self.origin = None  # Origin node ID
        self.destinations = []  # List of (node_id, severity) tuples
        self.severities = []  # ['Leve', 'Media', 'Crítica']
        
    def from_network(self, G, origin, destinations_with_severity):
        """Populate from NetworkX graph"""
        self.nodes = list(G.nodes())
        self.edges = list(G.edges(keys=True))
        
        # Extract edge data
        for u, v, key in self.edges:
            edge_attrs = G.edges[u, v, key]
            self.edge_data[(u, v, key)] = {
                'length': edge_attrs.get('length', 0),
                'capacity': edge_attrs.get('capacity', 50),
                'travel_time': edge_attrs.get('travel_time', 0)
            }
        
        self.origin = origin
        self.destinations = destinations_with_severity
        
        return self
    
    def get_required_speeds(self, r_min=30, r_max=70):
        """Generate random required speeds for each flow"""
        import random
        required_speeds = {}
        for dest, severity in self.destinations:
            # Critical emergencies might need higher speeds
            if severity == 'Crítica':
                speed = random.uniform(r_max * 0.8, r_max)
            elif severity == 'Media':
                speed = random.uniform(r_min + (r_max-r_min)*0.4, r_max * 0.9)
            else:  # Leve
                speed = random.uniform(r_min, r_min + (r_max-r_min)*0.6)
            required_speeds[dest] = speed
        return required_speeds