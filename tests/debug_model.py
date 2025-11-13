#!/usr/bin/env python3
"""
Debug script to analyze infeasibility issues
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / 'src'))

from visualization.network import NetworkManager
from optimization.data_interface import OptimizationData
from optimization.model import AmbulanceRoutingModel
import random

def debug_model():
    """Debug model infeasibility"""
    print("=" * 70)
    print("DEBUGGING MODEL INFEASIBILITY")
    print("=" * 70)
    
    # Load small network
    nm = NetworkManager(cache_dir="../data")
    center_point = (6.2331, -75.5839)
    
    graph = nm.load_network(center_point, method='circle', distance=560, use_cache=True)
    nm.assign_random_capacities(c_min=40, c_max=80)
    
    # Use simple case: 1 destination
    origin, destinations = nm.get_random_nodes(n_destinations=1)
    destinations_with_severity = [(destinations[0], 'Leve')]
    
    print(f"\nOrigin: {origin}")
    print(f"Destination: {destinations[0]} (Leve)")
    
    # Create optimization data
    opt_data = OptimizationData()
    opt_data.from_network(graph, origin, destinations_with_severity)
    
    # Build model with relaxed parameters
    model = AmbulanceRoutingModel(opt_data)
    costs = {'Leve': 100.0, 'Media': 250.0, 'Critica': 500.0}
    
    # Use lower required speeds
    model.set_parameters(costs=costs, r_min=20, r_max=40)
    
    print(f"\nCommodities: {model.commodities}")
    print(f"Required speeds: {model.required_speeds}")
    
    # Check capacity statistics
    capacities = [opt_data.edge_data[e]['capacity'] for e in opt_data.edges]
    print(f"\nCapacity statistics:")
    print(f"  Min: {min(capacities):.2f} km/h")
    print(f"  Max: {max(capacities):.2f} km/h")
    print(f"  Avg: {sum(capacities)/len(capacities):.2f} km/h")
    
    for commodity, speed in model.required_speeds.items():
        print(f"\nRequired speed for {commodity}: {speed:.2f} km/h")
        feasible_edges = sum(1 for c in capacities if c >= speed)
        print(f"  Edges with sufficient capacity: {feasible_edges}/{len(capacities)}")
    
    # Build and solve
    model.build_model()
    print(f"\nModel stats:")
    print(f"  Variables: {len(model.x_vars)}")
    print(f"  Constraints: {len(model.model.constraints)}")
    
    success = model.solve(time_limit=120)
    
    if success:
        print("\nSOLUTION FOUND!")
        model.print_solution()
    else:
        print("\nSTILL INFEASIBLE")
        print("\nTrying with even lower speeds...")
        
        # Try again with very low speeds
        model2 = AmbulanceRoutingModel(opt_data)
        model2.set_parameters(costs=costs, r_min=10, r_max=30)
        print(f"New required speeds: {model2.required_speeds}")
        
        model2.build_model()
        success2 = model2.solve(time_limit=120)
        
        if success2:
            print("\nSOLUTION FOUND WITH LOWER SPEEDS!")
            model2.print_solution()
        else:
            print("\nStill infeasible - may be network connectivity issue")

if __name__ == "__main__":
    debug_model()
