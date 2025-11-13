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
from optimization.model import AmbulanceRoutingModel
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
r_min = st.sidebar.slider("R_min (km/h)", 10, 30, 15, help="Minimum required speed")
r_max = st.sidebar.slider("R_max (km/h)", 30, 70, 35, help="Maximum required speed")
c_min = st.sidebar.slider("C_min (km/h)", 20, 50, 40, help="Minimum road capacity")
c_max = st.sidebar.slider("C_max (km/h)", 50, 100, 80, help="Maximum road capacity")

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
    st.session_state.model = None
    st.session_state.solution_summary = None
    st.session_state.optimization_run = False

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
                    
                    # Reset optimization when flows change
                    st.session_state.optimization_run = False
                    st.session_state.model = None
                    st.session_state.solution_summary = None
                
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
                
                # Add destination markers and routes if optimization was run
                severity_colors = {
                    'Leve': 'blue',
                    'Media': 'orange',
                    'Critica': 'red'
                }
                
                for dest, severity in st.session_state.destinations:
                    map_viz.add_destination_marker(dest, severity)
                
                # Add optimized routes if available
                if st.session_state.optimization_run and st.session_state.model:
                    routes = st.session_state.model.get_routes_as_paths()
                    summary = st.session_state.solution_summary
                    
                    for commodity, path in routes.items():
                        dest_node, severity_type = commodity
                        color = severity_colors.get(severity_type, 'blue')
                        
                        # Get required speed for this route
                        required_speed = st.session_state.model.required_speeds.get(commodity, 'N/A')
                        
                        # Create label with route info
                        route_info = summary.get(commodity, {})
                        label = f"{severity_type} Emergency"
                        if route_info:
                            label += f" - ${route_info['cost']:.2f}, {route_info['time_minutes']:.2f} min"
                        
                        map_viz.add_route(
                            path, 
                            color=color, 
                            weight=4, 
                            opacity=0.8,
                            label=label,
                            required_speed=required_speed if isinstance(required_speed, (int, float)) else None
                        )
                
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
    if st.session_state.network_loaded and st.session_state.optimization_data:
        
        # Solve button
        col_solve1, col_solve2 = st.columns([1, 3])
        with col_solve1:
            solve_button = st.button("Run Optimization", type="primary", use_container_width=True)
        with col_solve2:
            if st.session_state.optimization_run:
                st.success("Optimization completed successfully")
        
        if solve_button:
            with st.spinner("Building and solving optimization model..."):
                try:
                    # Create model
                    model = AmbulanceRoutingModel(st.session_state.optimization_data)
                    
                    # Set parameters
                    costs = {
                        'Leve': cost_leve,
                        'Media': cost_media,
                        'Critica': cost_critica
                    }
                    model.set_parameters(costs=costs, r_min=r_min, r_max=r_max)
                    
                    # Build model
                    model.build_model()
                    
                    st.info(f"Model built: {len(model.x_vars)} variables, {len(model.model.constraints)} constraints")
                    
                    # Solve
                    success = model.solve(time_limit=60)
                    
                    if success:
                        st.session_state.model = model
                        st.session_state.solution_summary = model.get_solution_summary()
                        st.session_state.optimization_run = True
                        st.success("Optimal solution found!")
                        st.rerun()
                    else:
                        st.error("Could not find feasible solution. Try adjusting parameters:")
                        st.markdown("""
                        - Increase C_max (higher road capacities)
                        - Decrease R_min (lower minimum speed requirements)
                        - Decrease R_max (lower maximum speed requirements)
                        """)
                        st.session_state.optimization_run = False
                        
                except Exception as e:
                    st.error(f"Error during optimization: {str(e)}")
                    st.exception(e)
                    st.session_state.optimization_run = False
        
        # Display results if optimization was run
        if st.session_state.optimization_run and st.session_state.solution_summary:
            st.divider()
            
            # Overall metrics
            st.subheader("Overall Performance")
            
            total_cost = sum(s['cost'] for s in st.session_state.solution_summary.values())
            total_time = sum(s['time_minutes'] for s in st.session_state.solution_summary.values())
            total_dist = sum(s['distance_km'] for s in st.session_state.solution_summary.values())
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Cost", f"${total_cost:.2f}")
            with col2:
                st.metric("Total Time", f"{total_time:.2f} min")
            with col3:
                st.metric("Total Distance", f"{total_dist:.2f} km")
            with col4:
                st.metric("Emergencies Served", f"{len(st.session_state.solution_summary)}/{len(st.session_state.destinations)}")
            
            st.divider()
            
            # Detailed results per emergency
            st.subheader("Route Details")
            
            for commodity, data in st.session_state.solution_summary.items():
                dest_node, severity_type = commodity
                
                severity_colors_bg = {
                    'Leve': '#e3f2fd',
                    'Media': '#fff3e0',
                    'Critica': '#ffebee'
                }
                
                with st.expander(f"🚑 {severity_type} Emergency - Node {dest_node}", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Cost", f"${data['cost']:.2f}")
                    with col2:
                        st.metric("Travel Time", f"{data['time_minutes']:.2f} min")
                    with col3:
                        st.metric("Distance", f"{data['distance_km']:.2f} km")
                    with col4:
                        required_speed = st.session_state.model.required_speeds.get(commodity, 0)
                        st.metric("Required Speed", f"{required_speed:.1f} km/h")
                    
                    # Path details
                    routes = st.session_state.model.get_routes_as_paths()
                    path = routes.get(commodity, [])
                    
                    if path:
                        st.markdown(f"**Route Path:** {len(path)} nodes")
                        st.markdown(f"Start: `{path[0]}` → End: `{path[-1]}`")
            
            st.divider()
            
            # Download solution
            st.subheader("Export Solution")
            
            import json
            solution_export = {
                'total_cost': total_cost,
                'total_time_minutes': total_time,
                'total_distance_km': total_dist,
                'routes': {}
            }
            
            routes = st.session_state.model.get_routes_as_paths()
            for commodity, path in routes.items():
                dest_node, severity_type = commodity
                solution_export['routes'][f"{severity_type}_{dest_node}"] = {
                    'destination': dest_node,
                    'severity': severity_type,
                    'path': path,
                    'metrics': st.session_state.solution_summary.get(commodity, {})
                }
            
            st.download_button(
                label="Download Solution (JSON)",
                data=json.dumps(solution_export, indent=2),
                file_name="ambulance_routing_solution.json",
                mime="application/json"
            )
        
        else:
            st.info("Click 'Run Optimization' to compute optimal ambulance routes")
            
            # Show current parameters
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
                st.write(f"- Leve: ${cost_leve:.2f}")
                st.write(f"- Media: ${cost_media:.2f}")
                st.write(f"- Critica: ${cost_critica:.2f}")
        
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
    - Optimal routing for multiple emergency severities
    
    **Study Area:**
    The default location is Hospital San Vicente Fundacion in Medellin, Colombia.
    Coordinates: 6°13'59.0"N 75°35'02.3"W
    
    **Model Components:**
    - **Severities:** Leve (mild), Media (moderate), Critica (critical)
    - **Ambulance Types:** Basic, Intermediate, Advanced Life Support
    - **Constraints:** Road capacities, flow conservation, speed requirements
    - **Objective:** Minimize total operational cost
    
    **Developers:**
    - Alexandra Vasco: Mathematical model and PuLP optimization
    - Roy Sandoval: Network extraction, UI, and visualization
    """)
    
    st.subheader("How to Use")
    st.markdown("""
    1. **Configure Network Area** (sidebar):
       - Set latitude/longitude (default: Hospital San Vicente)
       - Choose area shape (circle or square)
       - Set distance (radius or half-side length)
    
    2. **Load Network**:
       - Click "Load Network" button in Map Visualization tab
       - Wait for OSM data download (cached for faster subsequent loads)
    
    3. **Adjust Parameters** (sidebar):
       - **Speed Requirements:** R_min, R_max (ambulance speed needs)
       - **Road Capacities:** C_min, C_max (speed limits)
       - **Ambulance Costs:** Cost per hour for each severity type
       - **Emergencies:** Number of emergency locations to generate
    
    4. **Recalculate Options**:
       - **Recalculate Flows:** Generate new random emergency locations
       - **Recalculate Capacities:** Regenerate random road speed limits
    
    5. **Run Optimization**:
       - Go to "Results" tab
       - Click "Run Optimization" button
       - View optimal routes, costs, and metrics
    
    6. **View Results**:
       - Routes displayed on map (color-coded by severity)
       - Detailed metrics per emergency
       - Export solution as JSON
    
    **Tips for Feasible Solutions:**
    - Keep C_max > R_max (road capacity should exceed required speeds)
    - Use default values as starting point
    - If infeasible, increase C_max or decrease R_min/R_max
    """)
    
    st.subheader("Technical Details")
    st.markdown("""
    **Optimization Model:**
    - Type: Multi-commodity minimum cost flow
    - Solver: CBC (COIN-OR Branch and Cut)
    - Variables: Binary flow indicators x_ijk
    - Objective: Minimize Σ_k (α_k · Σ_(i,j) t_ij · x_ijk)
    
    **Constraints:**
    - Flow conservation at each node
    - Speed requirements: r_k · x_ijk ≤ c_ij
    - Each emergency served exactly once
    
    **Network:**
    - Source: OpenStreetMap via OSMnx
    - Type: Directed multigraph (drive network)
    - Processing: Strongly connected component extraction
    """)
