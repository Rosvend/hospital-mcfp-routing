import folium
import networkx as nx
from branca.element import Template, MacroElement


class MapVisualizer:
    """Handles map visualization with folium"""
    
    def __init__(self, graph, center_point):
        """
        Initialize map visualizer
        Parameters:
        - graph: NetworkX graph from OSMnx
        - center_point: (lat, lon) tuple for map center
        """
        self.graph = graph
        self.center_point = center_point
        self.map = None
        
    def create_base_map(self, zoom_start=15):
        """Create base folium map"""
        self.map = folium.Map(
            location=self.center_point,
            zoom_start=zoom_start,
            tiles='OpenStreetMap'
        )
        return self.map
    
    def add_network_edges(self, color='gray', weight=1, opacity=0.5):
        """Add all network edges to map"""
        if self.map is None:
            self.create_base_map()
        
        for u, v, key, data in self.graph.edges(keys=True, data=True):
            # Get coordinates
            u_coords = (self.graph.nodes[u]['y'], self.graph.nodes[u]['x'])
            v_coords = (self.graph.nodes[v]['y'], self.graph.nodes[v]['x'])
            
            # Create line
            folium.PolyLine(
                locations=[u_coords, v_coords],
                color=color,
                weight=weight,
                opacity=opacity,
                popup=f"Capacity: {data.get('capacity', 'N/A'):.1f} km/h"
            ).add_to(self.map)
        
        return self.map
    
    def add_route(self, path, color='blue', weight=3, opacity=0.8, label=None, required_speed=None):
        """
        Add a route (path) to the map
        Parameters:
        - path: list of node IDs
        - color: route color
        - weight: line thickness
        - opacity: line opacity
        - label: route label for popup
        - required_speed: required speed for this route
        """
        if self.map is None:
            self.create_base_map()
        
        if len(path) < 2:
            return
        
        # Create coordinate list
        coords = []
        for node in path:
            coords.append((self.graph.nodes[node]['y'], self.graph.nodes[node]['x']))
        
        # Create popup text
        popup_text = f"Route: {label if label else 'Unnamed'}"
        if required_speed:
            popup_text += f"<br>Required Speed: {required_speed:.1f} km/h"
        
        # Add route line
        folium.PolyLine(
            locations=coords,
            color=color,
            weight=weight,
            opacity=opacity,
            popup=folium.Popup(popup_text, max_width=250)
        ).add_to(self.map)
        
        return self.map
    
    def add_marker(self, node, color='red', icon='info-sign', popup_text=None):
        """Add a marker at a specific node"""
        if self.map is None:
            self.create_base_map()
        
        coords = (self.graph.nodes[node]['y'], self.graph.nodes[node]['x'])
        
        folium.Marker(
            location=coords,
            popup=popup_text or f"Node: {node}",
            icon=folium.Icon(color=color, icon=icon)
        ).add_to(self.map)
        
        return self.map
    
    def add_origin_marker(self, node):
        """Add marker for ambulance base/origin"""
        return self.add_marker(
            node, 
            color='green', 
            icon='home',
            popup_text="Ambulance Base"
        )
    
    def add_destination_marker(self, node, severity='Leve'):
        """Add marker for emergency destination"""
        color_map = {
            'Leve': 'blue',
            'Media': 'orange',
            'Critica': 'red'
        }
        
        icon_map = {
            'Leve': 'info-sign',
            'Media': 'exclamation-sign',
            'Critica': 'flash'
        }
        
        return self.add_marker(
            node,
            color=color_map.get(severity, 'blue'),
            icon=icon_map.get(severity, 'info-sign'),
            popup_text=f"Emergency: {severity}"
        )
    
    def add_legend(self):
        """Add a legend to the map"""
        if self.map is None:
            return
        
        legend_html = '''
        {% macro html(this, kwargs) %}
        <div style="
            position: fixed; 
            bottom: 50px; 
            left: 50px; 
            width: 220px; 
            height: auto; 
            background-color: white; 
            border:2px solid grey; 
            z-index:9999; 
            font-size:14px;
            padding: 10px;
            ">
            <p style="margin-bottom: 5px; font-weight: bold;">Legend</p>
            <p style="margin: 3px;"><i class="fa fa-home" style="color:green"></i> Ambulance Base</p>
            <p style="margin: 3px;"><i class="fa fa-info-circle" style="color:blue"></i> Emergency (Leve)</p>
            <p style="margin: 3px;"><i class="fa fa-exclamation-circle" style="color:orange"></i> Emergency (Media)</p>
            <p style="margin: 3px;"><i class="fa fa-bolt" style="color:red"></i> Emergency (Critica)</p>
            <p style="margin: 3px;"><span style="color:gray;">―</span> Road Network</p>
            <p style="margin: 3px;"><span style="color:blue;font-weight:bold;">―</span> Leve Route</p>
            <p style="margin: 3px;"><span style="color:orange;font-weight:bold;">―</span> Media Route</p>
            <p style="margin: 3px;"><span style="color:red;font-weight:bold;">―</span> Critica Route</p>
        </div>
        {% endmacro %}
        '''
        
        macro = MacroElement()
        macro._template = Template(legend_html)
        self.map.get_root().add_child(macro)
        
        return self.map
    
    def get_map(self):
        """Return the folium map object"""
        return self.map
