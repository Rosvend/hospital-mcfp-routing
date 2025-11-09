# app.py

import streamlit as st
import sys
from pathlib import Path
import random

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from visualization.network import NetworkManager
from visualization.map_display import MapVisualizer
from optimization.data_interface import OptimizationData
from streamlit_folium import st_folium

st.set_page_config(page_title="Ambulance Routing Optimizer", layout="wide")

st.title("Emergency Ambulance Routing Optimization")
st.markdown("Multi-commodity flow optimization for urban emergency response")

# Sidebar Configuration
st.sidebar.header("Configuration")

# Geographic parameters
st.sidebar.subheader("Network Area")
center_lat = st.sidebar.number_input("Latitude", value=6.2331, format="%.4f", help="Default: Hospital San Vicente (Medellin)")
center_lon = st.sidebar.number_input("Longitude", value=-75.5839, format="%.4f")
network_method = st.sidebar.selectbox("Area Shape", ["circle", "square"])
distance = st.sidebar.slider("Distance (m)", 400, 800, 560, help="Radius for circle or half-side for square")

# Optimization parameters
st.sidebar.subheader("Speed Parameters")
r_min = st.sidebar.slider("R_min (km/h)", 10, 50, 30, help="Minimum required speed")
r_max = st.sidebar.slider("R_max (km/h)", 50, 100, 70, help="Maximum required speed")
c_min = st.sidebar.slider("C_min (km/h)", 20, 60, 40, help="Minimum road capacity")
c_max = st.sidebar.slider("C_max (km/h)", 60, 120, 80, help="Maximum road capacity")

# Emergency configuration
st.sidebar.subheader("Emergencies")
n_emergencies = st.sidebar.slider("Number of emergencies", 1, 8, 3)

# Operational costs
st.sidebar.subheader("Ambulance Costs")
cost_leve = st.sidebar.number_input("Leve (Basic)", value=100.0, help="Cost per trip in USD")
cost_media = st.sidebar.number_input("Media (Intermediate)", value=250.0)
cost_critica = st.sidebar.number_input("Critica (Advanced)", value=500.0)

# Action buttons
st.sidebar.divider()
col1, col2 = st.sidebar.columns(2)
recalc_flows = col1.button("Recalculate Flows", use_container_width=True)
recalc_capacities = col2.button("Recalculate Capacities", use_container_width=True)

# Initialize session state
if 'network_loaded' not in st.session_state:
    st.session_state.network_loaded = False
    st.session_state.network_manager = NetworkManager()
    st.session_state.origin = None
    st.session_state.destinations = []
    st.session_state.optimization_data = None
    st.session_state.routes = None

# Main content area
tab1, tab2, tab3 = st.tabs(["Map Visualization", "Results", "About"])

with tab1:
    st.subheader("Network and Routes")
    
    # Load network button
    if st.button("Load Network") or st.session_state.network_loaded:
        with st.spinner("Loading road network from OpenStreetMap..."):
            try:
                # Load network using NetworkManager
                center_point = (center_lat, center_lon)
                graph = st.session_state.network_manager.load_network(
                    center_point=center_point,
                    method=network_method,
                    distance=distance,
                    use_cache=True
                )
                
                # Assign capacities if not already done or if recalculate button pressed
                if recalc_capacities or not st.session_state.network_loaded:
                    st.session_state.network_manager.assign_random_capacities(c_min, c_max)
                
                # Select origin and destinations
                if not st.session_state.network_loaded or recalc_flows:
                    origin, destinations = st.session_state.network_manager.get_random_nodes(
                        n_destinations=n_emergencies
                    )
                    st.session_state.origin = origin
                    
                    # Assign random severities to destinations
                    severities = ['Leve', 'Media', 'Critica']
                    destinations_with_severity = [
                        (dest, random.choice(severities)) for dest in destinations
                    ]
                    st.session_state.destinations = destinations_with_severity
                    
                    # Create optimization data structure
                    opt_data = OptimizationData()
                    opt_data.from_network(graph, origin, destinations_with_severity)
                    st.session_state.optimization_data = opt_data
                
                st.success(f"Network loaded: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
                st.session_state.network_loaded = True
                
                # Create map visualization
                st.subheader("Network Map")
                
                # Create map visualizer
                map_viz = MapVisualizer(graph, center_point)
                map_viz.create_base_map(zoom_start=15)
                
                # Add network edges (light background)
                map_viz.add_network_edges(color='lightgray', weight=1, opacity=0.3)
                
                # Add origin marker
                map_viz.add_origin_marker(st.session_state.origin)
                
                # Add destination markers
                severity_colors = {
                    'Leve': 'blue',
                    'Media': 'orange',
                    'Critica': 'red'
                }
                
                for dest, severity in st.session_state.destinations:
                    map_viz.add_destination_marker(dest, severity)
                
                # Add legend
                map_viz.add_legend()
                
                # Display map
                st_folium(map_viz.get_map(), width=1200, height=600)
                
                # Display network statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Nodes", len(graph.nodes))
                with col2:
                    st.metric("Edges", len(graph.edges))
                with col3:
                    st.metric("Origin Node", st.session_state.origin)
                with col4:
                    st.metric("Emergencies", len(st.session_state.destinations))
                
                # Display destination details
                st.subheader("Emergency Locations")
                dest_data = []
                for i, (dest, severity) in enumerate(st.session_state.destinations, 1):
                    coords = st.session_state.network_manager.get_node_coordinates(dest)
                    dest_data.append({
                        'Emergency': i,
                        'Node ID': dest,
                        'Severity': severity,
                        'Latitude': f"{coords[0]:.6f}",
                        'Longitude': f"{coords[1]:.6f}"
                    })
                
                st.table(dest_data)
                
            except Exception as e:
                st.error(f"Error loading network: {str(e)}")
                st.exception(e)
            
with tab2:
    st.subheader("Optimization Results")
    if st.session_state.network_loaded:
        st.info("Optimization model integration pending (Developer A's work)")
        st.markdown("""
        When the optimization model is ready, this section will display:
        - Optimal routes for each emergency
        - Total operational cost
        - Travel times and distances
        - Resource utilization metrics
        """)
        
        # Show current parameters that will be used for optimization
        st.subheader("Current Optimization Parameters")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Speed Requirements:**")
            st.write(f"- R_min: {r_min} km/h")
            st.write(f"- R_max: {r_max} km/h")
            st.write(f"- C_min: {c_min} km/h")
            st.write(f"- C_max: {c_max} km/h")
        
        with col2:
            st.markdown("**Operational Costs:**")
            st.write(f"- Leve: ${cost_leve}")
            st.write(f"- Media: ${cost_media}")
            st.write(f"- Critica: ${cost_critica}")
        
    else:
        st.warning("Please load a network first")

with tab3:
    st.subheader("About This Project")
    st.markdown("""
    This application implements a multi-commodity flow optimization model
    for emergency ambulance routing in urban areas.
    
    **Features:**
    - Real road network extraction using OSMnx
    - Multi-commodity flow optimization using PuLP
    - Interactive parameter configuration
    - Visual route display on real maps
    
    **Study Area:**
    The default location is Hospital San Vicente Fundacion in Medellin, Colombia.
    Coordinates: 6deg13'59.0"N 75deg35'02.3"W
    
    **Model Components:**
    - **Severities:** Leve (mild), Media (moderate), Critica (critical)
    - **Ambulance Types:** Basic, Intermediate, Advanced Life Support
    - **Constraints:** Road capacities, flow requirements, cost optimization
    
    **Developers:**
    - Developer A: Mathematical model and PuLP optimization
    - Developer B: Network extraction, UI, and visualization
    """)
    
    st.subheader("How to Use")
    st.markdown("""
    1. Configure the network area in the sidebar (latitude, longitude, distance)
    2. Click "Load Network" to download the road network
    3. Adjust speed parameters and costs as needed
    4. Click "Recalculate Flows" to generate new emergency locations
    5. Click "Recalculate Capacities" to regenerate road capacities
    6. View the network map and optimization results
    """)